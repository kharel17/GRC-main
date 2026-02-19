
import { ISOControl, ISOEvidence, ISOAuditLog, ISOComplianceStats } from '@/types/iso27001';
import { api } from './api-client';

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
      if (!localStorage.getItem(this.CONTROLS_KEY)) {
        localStorage.setItem(this.CONTROLS_KEY, '[]');
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
  async getControls(): Promise<ISOControl[]> {
    return api.get<ISOControl[]>('/controls');
  }

  async getControlById(id: string): Promise<ISOControl | null> {
    try {
      return await api.get<ISOControl>(`/controls/${id}`);
    } catch {
      return null;
    }
  }

  async saveControl(control: ISOControl): Promise<ISOControl> {
    return api.post<ISOControl>('/controls', control);
  }

  async updateControl(control: ISOControl): Promise<ISOControl> {
    return api.put<ISOControl>(`/controls/${control.id}`, control);
  }

  async getEvidence(controlId: string): Promise<ISOEvidence[]> {
    return api.get<ISOEvidence[]>(`/evidence?control_id=${controlId}`);
  }

  async getAllEvidence(): Promise<ISOEvidence[]> {
    return api.get<ISOEvidence[]>('/evidence');
  }

  async uploadEvidence(evidence: ISOEvidence): Promise<ISOEvidence> {
    return api.post<ISOEvidence>('/evidence', evidence);
  }

  async deleteEvidence(id: string): Promise<void> {
    return api.delete(`/evidence/${id}`);
  }

  async getAuditLogs(entityId?: string): Promise<ISOAuditLog[]> {
    const query = entityId ? `?entity_id=${entityId}` : '';
    return api.get<ISOAuditLog[]>(`/audit-logs${query}`);
  }

  async logAction(logData: Omit<ISOAuditLog, 'id' | 'timestamp'>): Promise<ISOAuditLog> {
    return api.post<ISOAuditLog>('/audit-logs', logData);
  }

  async getComplianceStats(): Promise<ISOComplianceStats> {
    return api.get<ISOComplianceStats>('/compliance/stats');
  }
}

// =============================================================================
// Export the active adapter based on env var
// =============================================================================

function createStorageService(): StorageService {
  if (typeof window === 'undefined') {
    // Server-side: always use local (no localStorage, but returns empty arrays)
    return new LocalStorageAdapter();
  }
  if (api.isMock) {
    return new LocalStorageAdapter();
  }
  return new ApiStorageAdapter();
}

export const storageService = createStorageService();
