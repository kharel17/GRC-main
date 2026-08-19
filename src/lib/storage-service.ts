
import { ISOControl, ISOEvidence, ISOAuditLog, ISOComplianceStats, ISOControlStatus } from '@/types';
import { api } from './api-client';
import isoData from '@/data/iso27001-controls.json';


let isUsingFallback = false;
export const getIsUsingFallback = () => isUsingFallback;


export interface StorageService {
  // Controls
  getControls(): Promise<ISOControl[]>;
  getControlById(id: string): Promise<ISOControl | null>;
  saveControl(control: ISOControl): Promise<ISOControl>;
  updateControl(control: ISOControl): Promise<ISOControl>;

  // Evidence
  getEvidence(controlId: string): Promise<ISOEvidence[]>;
  getAllEvidence(): Promise<ISOEvidence[]>;
  uploadEvidence(evidence: ISOEvidence): Promise<ISOEvidence>;
  deleteEvidence(id: string): Promise<void>;

  // Audit Logs
  getAuditLogs(entityId?: string): Promise<ISOAuditLog[]>;
  logAction(log: Omit<ISOAuditLog, 'id' | 'timestamp'>): Promise<ISOAuditLog>;

  // Compliance Stats
  getComplianceStats(): Promise<ISOComplianceStats>;
}

// =============================================================================
// Local Storage Adapter (demo/development)
// =============================================================================

export class LocalStorageAdapter implements StorageService {
  private readonly CONTROLS_KEY = 'iso_controls';
  private readonly EVIDENCE_KEY = 'iso_evidence';
  private readonly AUDIT_KEY = 'iso_audit_logs';

  constructor() {
    if (typeof window !== 'undefined') {
      // Only seed if truly empty — never overwrite existing data
      const existingControls = localStorage.getItem(this.CONTROLS_KEY);
      const isEmpty = !existingControls || JSON.parse(existingControls).length === 0;

      if (isEmpty) {
        // Map controls from the JSON to the ISOControl format
        const allControls = isoData.controls.map((control: any) => ({
          ...control,
          status: control.status || 'not_started',
          evidenceIds: [],
          riskIds: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        }));
        localStorage.setItem(this.CONTROLS_KEY, JSON.stringify(allControls));
      }

      if (!localStorage.getItem(this.EVIDENCE_KEY)) {
        localStorage.setItem(this.EVIDENCE_KEY, '[]');
      }
      if (!localStorage.getItem(this.AUDIT_KEY)) {
        localStorage.setItem(this.AUDIT_KEY, '[]');
      }
    }
  }

  async getControls(): Promise<ISOControl[]> {
    if (typeof window === 'undefined') return [];
    return JSON.parse(localStorage.getItem(this.CONTROLS_KEY) || '[]');
  }

  async getControlById(id: string): Promise<ISOControl | null> {
    const controls = await this.getControls();
    return controls.find(c => c.id === id) || null;
  }

  async saveControl(control: ISOControl): Promise<ISOControl> {
    const controls = await this.getControls();
    const index = controls.findIndex(c => c.id === control.id);
    if (index >= 0) {
      controls[index] = control;
    } else {
      controls.push(control);
    }
    localStorage.setItem(this.CONTROLS_KEY, JSON.stringify(controls));
    return control;
  }

  async updateControl(control: ISOControl): Promise<ISOControl> {
    return this.saveControl(control);
  }

  async getEvidence(controlId: string): Promise<ISOEvidence[]> {
    if (typeof window === 'undefined') return [];
    const allEvidence: ISOEvidence[] = JSON.parse(localStorage.getItem(this.EVIDENCE_KEY) || '[]');
    return allEvidence.filter(e => e.controlId === controlId);
  }

  async getAllEvidence(): Promise<ISOEvidence[]> {
    if (typeof window === 'undefined') return [];
    return JSON.parse(localStorage.getItem(this.EVIDENCE_KEY) || '[]');
  }

  async uploadEvidence(evidence: ISOEvidence): Promise<ISOEvidence> {
    const allEvidence: ISOEvidence[] = JSON.parse(localStorage.getItem(this.EVIDENCE_KEY) || '[]');
    allEvidence.push(evidence);
    localStorage.setItem(this.EVIDENCE_KEY, JSON.stringify(allEvidence));
    return evidence;
  }

  async deleteEvidence(id: string): Promise<void> {
    const allEvidence: ISOEvidence[] = JSON.parse(localStorage.getItem(this.EVIDENCE_KEY) || '[]');
    const filtered = allEvidence.filter(e => e.id !== id);
    localStorage.setItem(this.EVIDENCE_KEY, JSON.stringify(filtered));
  }

  async getAuditLogs(entityId?: string): Promise<ISOAuditLog[]> {
    if (typeof window === 'undefined') return [];
    const logs: ISOAuditLog[] = JSON.parse(localStorage.getItem(this.AUDIT_KEY) || '[]');
    if (entityId) {
      return logs.filter(l => l.entityId === entityId).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    }
    return logs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }

  async logAction(logData: Omit<ISOAuditLog, 'id' | 'timestamp'>): Promise<ISOAuditLog> {
    const logs: ISOAuditLog[] = JSON.parse(localStorage.getItem(this.AUDIT_KEY) || '[]');
    const newLog: ISOAuditLog = {
      ...logData,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
    };
    logs.push(newLog);
    localStorage.setItem(this.AUDIT_KEY, JSON.stringify(logs));
    return newLog;
  }

  async getComplianceStats(): Promise<ISOComplianceStats> {
    const controls = await this.getControls();
    const total = controls.length;
    const implemented = controls.filter(c => c.status === 'implemented').length;
    const inProgress = controls.filter(c => c.status === 'in_progress').length;
    const notStarted = controls.filter(c => c.status === 'not_started').length;
    const notApplicable = controls.filter(c => c.status === 'not_applicable').length;
    const applicableTotal = total - notApplicable;
    const score = applicableTotal > 0 ? Math.round((implemented / applicableTotal) * 100) : 0;

    return {
      totalControls: total,
      implementedControls: implemented,
      inProgressControls: inProgress,
      notStartedControls: notStarted,
      notApplicableControls: notApplicable,
      complianceScore: score,
    };
  }
}

// =============================================================================
// API Adapter (production — calls FastAPI backend)
// =============================================================================

export class ApiStorageAdapter implements StorageService {
  private fallback: LocalStorageAdapter;

  constructor(fallback: LocalStorageAdapter) {
    this.fallback = fallback;
  }

  private isIsoAnnexId(id: string): boolean {
    return /^\d+\.\d+$/.test(id) || id.startsWith('A.');
  }

  private mapSoAEntryToControl(entry: any): ISOControl {
    return {
      id: entry.control_annex,
      clauseId: entry.clause_id,
      annex: entry.control_annex,
      title: entry.control_title,
      description: entry.control_description,
      status: entry.status as ISOControlStatus,
      ownerId: entry.responsible_id || "",
      ownerName: entry.responsible_name || "",
      evidenceCount: entry.evidence_count || 0,
      isApplicable: entry.is_applicable,
      notes: entry.notes || "",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    } as any;
  }

  private mapCAToControl(ca: any): ISOControl {
    // Merge with static data to get title/description if missing
    const staticInfo = isoData.controls.find(c => c.id === ca.control_annex);
    return {
      id: ca.control_annex, 
      realId: ca.id,        
      title: staticInfo?.title || `Control ${ca.control_annex}`,
      description: staticInfo?.description || "",
      status: ca.status || 'not_started',
      ownerId: ca.responsible_id || "",
      notes: ca.notes || "",
      isApplicable: ca.is_applicable,
      justification: ca.justification,
      iso_clause: ca.control_annex,
      createdAt: ca.created_at || new Date().toISOString(),
      updatedAt: ca.updated_at || new Date().toISOString(),
    } as any;
  }

  async getControls(): Promise<ISOControl[]> {
    try {
      const response = await api.get<{ entries: any[] }>('/control-applicability/soa');
      return response.entries.map(entry => this.mapSoAEntryToControl(entry));
    } catch (err) {
      console.warn('[ApiStorageAdapter] getControls failed, falling back', err);
      return this.fallback.getControls();
    }
  }

  async getControlById(id: string): Promise<ISOControl | null> {
    try {
      if (this.isIsoAnnexId(id)) {
        const ca = await api.get<any>(`/control-applicability/annex/${id}`);
        return this.mapCAToControl(ca);
      }
      // Try control-applicability by UUID first
      try {
        const ca = await api.get<any>(`/control-applicability/${id}`);
        if (ca && ca.control_annex) {
          return this.mapCAToControl(ca);
        }
      } catch {
        // Fallback to general controls table
      }
      return await api.get<ISOControl>(`/controls/${id}/`);
    } catch (err) {
      console.warn('[ApiStorageAdapter] getControlById failed, falling back', err);
      return this.fallback.getControlById(id);
    }
  }

  async saveControl(control: ISOControl): Promise<ISOControl> {
    try {
      return await api.post<ISOControl>('/controls/', control);
    } catch (err) {
      console.warn('[ApiStorageAdapter] saveControl failed, falling back', err);
      return this.fallback.saveControl(control);
    }
  }

  async updateControl(control: ISOControl): Promise<ISOControl> {
    try {
      if (this.isIsoAnnexId(control.id)) {
        // Find existing CA record to get its UUID
        const ca = await api.get<any>(`/control-applicability/annex/${control.id}`);
        const updateData = {
          status: control.status,
          notes: control.notes,
          responsible_id: control.ownerId === 'unassigned' ? null : control.ownerId,
        };
        const updated = await api.put<any>(`/control-applicability/${ca.id}/`, updateData);
        return this.mapCAToControl(updated);
      }
      return await api.put<ISOControl>(`/controls/${control.id}/`, control);
    } catch (err) {
      console.warn('[ApiStorageAdapter] updateControl failed, falling back', err);
      return this.fallback.updateControl(control);
    }
  }

  private mapEvidenceToISOEvidence(item: any): ISOEvidence {
    return {
      id: item.id,
      title: item.title || item.file_name || 'Evidence File',
      description: item.description || '',
      file_url: item.file_url,
      fileUrl: item.file_url || '',
      file_name: item.file_name,
      fileName: item.file_name || item.title || 'Evidence File',
      file_type: item.file_type,
      fileType: item.file_type || 'document',
      file_size: item.file_size,
      fileSize: item.file_size || 0,
      control_id: item.related_id,
      controlId: item.related_id || '',
      uploaded_by: item.uploaded_by,
      uploadedBy: item.uploaded_by || '',
      uploadedByName: item.uploaded_by_name || item.uploaded_by || 'User',
      uploaded_at: item.uploaded_at || new Date().toISOString(),
      uploadedAt: item.uploaded_at || new Date().toISOString(),
      version: item.version || 1,
    };
  }

  async getEvidence(controlId: string): Promise<ISOEvidence[]> {
    try {
      const list = await api.get<any[]>(`/evidence/?control_id=${controlId}`);
      return (list || []).map(item => this.mapEvidenceToISOEvidence(item));
    } catch (err) {
      console.warn('[ApiStorageAdapter] getEvidence failed, falling back', err);
      return this.fallback.getEvidence(controlId);
    }
  }

  async getAllEvidence(): Promise<ISOEvidence[]> {
    try {
      const list = await api.get<any[]>('/evidence/');
      const rawList = (list || []).map(item => this.mapEvidenceToISOEvidence(item));

      // Resolve UUID related_ids to human-readable Annex IDs (e.g. "5.1")
      try {
        const controls = await this.getControls();
        const controlMap = new Map<string, string>();
        controls.forEach((c: any) => {
          if (c.realId) controlMap.set(c.realId, c.id || c.annex);
          if (c.id) controlMap.set(c.id, c.id || c.annex);
        });

        return rawList.map(ev => {
          const resolved = controlMap.get(ev.controlId) || ev.controlId;
          return {
            ...ev,
            controlId: resolved,
            control_id: resolved,
          };
        });
      } catch {
        return rawList;
      }
    } catch (err) {
      console.warn('[ApiStorageAdapter] getAllEvidence failed, falling back', err);
      return this.fallback.getAllEvidence();
    }
  }

  async uploadEvidence(evidence: ISOEvidence): Promise<ISOEvidence> {
    try {
      return await api.post<ISOEvidence>('/evidence/', evidence);
    } catch (err) {
      console.warn('[ApiStorageAdapter] uploadEvidence failed, falling back', err);
      return this.fallback.uploadEvidence(evidence);
    }
  }

  async deleteEvidence(id: string): Promise<void> {
    try {
      return await api.delete(`/evidence/${id}/`);
    } catch (err) {
      console.warn('[ApiStorageAdapter] deleteEvidence failed, falling back', err);
      return this.fallback.deleteEvidence(id);
    }
  }

  async getAuditLogs(entityId?: string): Promise<ISOAuditLog[]> {
    try {
      const query = entityId ? `?entity_id=${entityId}` : '';
      return await api.get<ISOAuditLog[]>(`/audit-logs/${query}/`);
    } catch (err) {
      console.warn('[ApiStorageAdapter] getAuditLogs failed, falling back', err);
      return this.fallback.getAuditLogs(entityId);
    }
  }

  async logAction(logData: Omit<ISOAuditLog, 'id' | 'timestamp'>): Promise<ISOAuditLog> {
    try {
      return await api.post<ISOAuditLog>('/audit-logs/', logData);
    } catch (err) {
      console.warn('[ApiStorageAdapter] logAction failed, falling back', err);
      return this.fallback.logAction(logData);
    }
  }

  async getComplianceStats(): Promise<ISOComplianceStats> {
    try {
      const res = await api.get<any>('/control-applicability/compliance-score');
      if (res) {
        const implemented = res.implemented ?? res.implemented_count ?? 0;
        const inProgress = res.in_progress ?? res.in_progress_count ?? 0;
        const notStarted = res.not_started ?? res.not_started_count ?? 0;
        const notApplicable = res.not_applicable ?? res.not_applicable_count ?? 0;
        const total = res.total_controls ?? ((implemented + inProgress + notStarted + notApplicable) || 93);
        const pct = res.compliance_percentage ?? res.overall_percentage ?? res.complianceScore ?? 0;

        return {
          totalControls: total,
          implementedControls: implemented,
          inProgressControls: inProgress,
          notStartedControls: notStarted,
          notApplicableControls: notApplicable,
          complianceScore: Math.round(pct),
        };
      }
    } catch (err) {
      console.warn('[ApiStorageAdapter] /control-applicability/compliance-score failed, trying /compliance/stats', err);
    }

    try {
      return await api.get<ISOComplianceStats>('/compliance/stats');
    } catch (err) {
      console.warn('[ApiStorageAdapter] getComplianceStats failed, falling back', err);
      isUsingFallback = true;
      return this.fallback.getComplianceStats();
    }
  }
}

// =============================================================================
// Export the active adapter based on env var
// =============================================================================

function createStorageService(): StorageService {
  const local = new LocalStorageAdapter();
  if (typeof window === 'undefined') {
    return local;
  }
  if (api.isMock) {
    return local;
  }
  return new ApiStorageAdapter(local);
}

export const storageService = createStorageService();
