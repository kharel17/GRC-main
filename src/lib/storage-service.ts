
import { ISOControl, ISOEvidence, ISOAuditLog, ISOComplianceStats } from '@/types';
import { api } from './api-client';

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
  private fallback: LocalStorageAdapter;

  constructor(fallback: LocalStorageAdapter) {
    this.fallback = fallback;
  }

  async getControls(): Promise<ISOControl[]> {
    try {
      return await api.get<ISOControl[]>('/controls/');
    } catch (err) {
      console.warn('[ApiStorageAdapter] getControls failed, falling back', err);
      return this.fallback.getControls();
    }
  }

  async getControlById(id: string): Promise<ISOControl | null> {
    try {
      return await api.get<ISOControl>(`/controls/${id}`);
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
      return await api.put<ISOControl>(`/controls/${control.id}`, control);
    } catch (err) {
      console.warn('[ApiStorageAdapter] updateControl failed, falling back', err);
      return this.fallback.updateControl(control);
    }
  }

  async getEvidence(controlId: string): Promise<ISOEvidence[]> {
    try {
      return await api.get<ISOEvidence[]>(`/evidence?control_id=${controlId}`);
    } catch (err) {
      console.warn('[ApiStorageAdapter] getEvidence failed, falling back', err);
      return this.fallback.getEvidence(controlId);
    }
  }

  async getAllEvidence(): Promise<ISOEvidence[]> {
    try {
      return await api.get<ISOEvidence[]>('/evidence');
    } catch (err) {
      console.warn('[ApiStorageAdapter] getAllEvidence failed, falling back', err);
      return this.fallback.getAllEvidence();
    }
  }

  async uploadEvidence(evidence: ISOEvidence): Promise<ISOEvidence> {
    try {
      return await api.post<ISOEvidence>('/evidence', evidence);
    } catch (err) {
      console.warn('[ApiStorageAdapter] uploadEvidence failed, falling back', err);
      return this.fallback.uploadEvidence(evidence);
    }
  }

  async deleteEvidence(id: string): Promise<void> {
    try {
      return await api.delete(`/evidence/${id}`);
    } catch (err) {
      console.warn('[ApiStorageAdapter] deleteEvidence failed, falling back', err);
      return this.fallback.deleteEvidence(id);
    }
  }

  async getAuditLogs(entityId?: string): Promise<ISOAuditLog[]> {
    try {
      const query = entityId ? `?entity_id=${entityId}` : '';
      return await api.get<ISOAuditLog[]>(`/audit-logs/${query}`);
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
