
import {
  ISOControl,
  ISOControlStatus,
  ISOEvidence,
  ISOComplianceStats,
  ISOClause,
  ISOAuditLog
} from '@/types/iso27001';
import { storageService } from './storage-service';
import { DataValidator } from './data-validation';
import isoData from '@/data/iso27001-controls.json';
import { UserRole } from '@/types/user';

// Initialize data if needed
// This effectively acts as a database migration/seeder for the local session
if (typeof window !== 'undefined') {
  // Safe initialization that catches network/auth errors to prevent app crashes
  storageService.getControls()
    .then(controls => {
      if (controls && controls.length === 0) {
        console.log('ISO Controls empty, seeding initial data...');
        const initialControls: ISOControl[] = isoData.controls.map(c => ({
          ...c,
          status: c.status as ISOControlStatus,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }));

        // Save all initial controls safely
        Promise.all(initialControls.map(c => storageService.saveControl(c)))
          .then(() => console.log('ISO Controls initialized successfully'))
          .catch(err => console.error('Failed to save initial controls:', err));
      }
    })
    .catch(err => {
      // Crucial: Catch the 401 or network errors so they don't bubble up as "Failed to fetch" crashes!
      console.warn('Skipping ISO Controls initialization (expected if logged out or backend is loading):', err.message || err);
    });
}

export const isoService = {
  // ===========================================================================
  // Clauses & Controls
  // ===========================================================================

  async getClauses(): Promise<ISOClause[]> {
    return isoData.clauses;
  },

  async getControls(): Promise<ISOControl[]> {
    return storageService.getControls();
  },

  async getControlById(id: string): Promise<ISOControl | null> {
    return storageService.getControlById(id);
  },

  async updateControlStatus(
    id: string,
    status: ISOControlStatus,
    userCtx: { id: string; name: string; role: UserRole },
    notes?: string
  ): Promise<ISOControl> {
    // 1. RBAC Check
    if (!DataValidator.canUpdateControl(userCtx.role)) {
      throw new Error('Unauthorized: Insufficient permissions to update control');
    }

    const control = await storageService.getControlById(id);
    if (!control) throw new Error('Control not found');

    // 2. Validation
    const validation = DataValidator.validateControlUpdate({ ...control, status }, userCtx.role);
    if (!validation.valid) {
      throw new Error(validation.error);
    }

    const oldValue = control.status;
    const updatedControl: ISOControl = {
      ...control,
      status,
      updatedAt: new Date().toISOString(),
      notes: notes ? notes : control.notes, // simple append or replace logic could be here
    };

    // 3. Save
    await storageService.updateControl(updatedControl);

    // 4. Audit Log
    await storageService.logAction({
      action: 'update',
      entityId: id,
      entityType: 'control',
      userId: userCtx.id,
      userName: userCtx.name,
      details: `Updated status from ${oldValue} to ${status}`,
      changes: [{ field: 'status', oldValue, newValue: status }]
    });

    return updatedControl;
  },

  async assignOwner(
    id: string,
    ownerId: string,
    ownerName: string,
    userCtx: { id: string; name: string; role: UserRole }
  ): Promise<ISOControl> {
    if (!DataValidator.canManageFramework(userCtx.role)) { // Only admin can assign usually, or maybe analyst?
      // Let's assume admins and maybe analysts can assign
      if (userCtx.role !== 'admin' && userCtx.role !== 'analyst') {
        throw new Error('Unauthorized: Only Admins and Analysts can assign owners');
      }
    }

    const control = await storageService.getControlById(id);
    if (!control) throw new Error('Control not found');

    const updatedControl: ISOControl = {
      ...control,
      ownerId,
      ownerName,
      updatedAt: new Date().toISOString(),
    };

    await storageService.updateControl(updatedControl);

    await storageService.logAction({
      action: 'update',
      entityId: id,
      entityType: 'control',
      userId: userCtx.id,
      userName: userCtx.name,
      details: `Assigned owner to ${ownerName}`,
      changes: [{ field: 'ownerId', oldValue: control.ownerId, newValue: ownerId }]
    });

    return updatedControl;
  },

  // ===========================================================================
  // Evidence
  // ===========================================================================

  async getEvidenceForControl(controlId: string): Promise<ISOEvidence[]> {
    return storageService.getEvidence(controlId);
  },

  async getAllEvidence(): Promise<ISOEvidence[]> {
    return storageService.getAllEvidence();
  },

  async uploadEvidence(
    controlId: string,
    file: File,
    userCtx: { id: string; name: string; role: UserRole },
    description?: string
  ): Promise<ISOEvidence> {
    // 1. RBAC
    if (!DataValidator.canUploadEvidence(userCtx.role)) {
      throw new Error('Unauthorized: Insufficient permissions to upload evidence');
    }

    // 2. Validation
    const validation = DataValidator.validateEvidence(file);
    if (!validation.valid) {
      throw new Error(validation.error);
    }

    // 3. Mock Upload (Storage Abstraction)
    // In a real app, this would upload to S3/Blob and return a URL
    // Here we act as if we did it.
    const evidence: ISOEvidence = {
      id: crypto.randomUUID(),
      title: file.name,
      description,
      fileUrl: URL.createObjectURL(file), // Mock URL for local session
      fileName: file.name,
      fileType: file.type,
      fileSize: file.size,
      controlId,
      uploadedBy: userCtx.id,
      uploadedByName: userCtx.name,
      uploadedAt: new Date().toISOString(),
      version: 1,
    };

    const savedEvidence = await storageService.uploadEvidence(evidence);

    // 4. Update Control (link evidence)
    const control = await storageService.getControlById(controlId);
    if (control) {
      const evidenceIds = control.evidenceIds || [];
      evidenceIds.push(savedEvidence.id);
      await storageService.updateControl({ ...control, evidenceIds });
    }

    // 5. Audit Log
    await storageService.logAction({
      action: 'upload_evidence',
      entityId: controlId, // Log against control? or evidence?
      entityType: 'control',
      userId: userCtx.id,
      userName: userCtx.name,
      details: `Uploaded evidence: ${file.name}`
    });

    return savedEvidence;
  },

  async deleteEvidence(
    id: string,
    controlId: string,
    userCtx: { id: string; name: string; role: UserRole }
  ): Promise<void> {
    if (!DataValidator.canManageFramework(userCtx.role)) {
      // Only admin/analyst
      if (userCtx.role === 'manager') throw new Error('Unauthorized');
    }

    await storageService.deleteEvidence(id);

    // Update control
    const control = await storageService.getControlById(controlId);
    if (control && control.evidenceIds) {
      const evidenceIds = control.evidenceIds.filter(eid => eid !== id);
      await storageService.updateControl({ ...control, evidenceIds });
    }

    await storageService.logAction({
      action: 'delete_evidence',
      entityId: controlId,
      entityType: 'control',
      userId: userCtx.id,
      userName: userCtx.name,
      details: `Deleted evidence ID: ${id}`
    });
  },

  // ===========================================================================
  // Compliance & Reporting
  // ===========================================================================

  async getComplianceStats(): Promise<ISOComplianceStats> {
    return storageService.getComplianceStats();
  },

  async getAuditLogs(entityId?: string, userRole?: UserRole): Promise<ISOAuditLog[]> {
    // Only Admin/Manager can view audit logs usually? The plan says Analyst can view reports.
    // Permissions.ts says: admin: view_audit_logs, manager: view_audit_logs, analyst: view_audit_logs 
    // Wait, Permissions.ts says analyst: view_audit_logs. So all can view.
    return storageService.getAuditLogs(entityId);
  },

  // ===========================================================================
  // Risk Integration
  // ===========================================================================

  async linkRiskToControl(
    controlId: string,
    riskId: string,
    userCtx: { id: string; name: string; role: UserRole }
  ): Promise<void> {
    if (userCtx.role === 'manager') throw new Error('Unauthorized');

    const control = await storageService.getControlById(controlId);
    if (!control) throw new Error('Control not found');

    const riskIds = control.riskIds || [];
    if (!riskIds.includes(riskId)) {
      riskIds.push(riskId);
      await storageService.updateControl({ ...control, riskIds });

      await storageService.logAction({
        action: 'link_risk',
        entityId: controlId,
        entityType: 'control',
        userId: userCtx.id,
        userName: userCtx.name,
        details: `Linked Risk ID: ${riskId}`
      });
    }
  }
};
