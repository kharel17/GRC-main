/**
 * GRC Platform - Data Service
 *
 * Centralized data fetching: calls the real FastAPI backend.
 * Gracefully handles empty states when API is unreachable or no data exists.
 *
 * Every page should use the functions here instead of direct API calls.
 */
import { api } from './api-client';
import { supabase } from './supabase';

// import {
//   mockRisks,
//   mockRiskCategories,
//   mockControls,
//   mockComplianceItems,
//   mockEvidence,
//   mockAuditLogs,
//   mockTickets,
//   mockOrganization,
//   mockAssets,
//   mockDocumentAnalyses,
// } from './mock-data';
import { 
  Risk, 
  RiskCategory, 
  Control, 
  ComplianceItem, 
  Evidence, 
  AuditLog, 
  Ticket, 
  Organization, 
  Asset, 
  DocumentAnalysis 
} from '@/types';

// -- Helper --────────

async function fetchOrFallback<T>(endpoint: string, fallback: T): Promise<T> {
  // Mock mode is strictly disabled in this version to enforce real data usage.
  try {
    return await api.get<T>(endpoint);
  } catch (err) {
    // Use warn (not error) — this is a gracefully-handled fallback, not a crash.
    // Common causes: backend not yet seeded (e.g. control-applicability table empty),
    // or service temporarily unavailable. The UI will render safely with the fallback.
    console.warn(`[DataService] ${endpoint} unavailable, using fallback:`, (err as Error)?.message ?? err);
    // Return empty array/default on failure to prevent UI crashes.
    return (Array.isArray(fallback) ? [] : fallback) as unknown as T;
  }
}

// -- Risk --────────
export async function fetchRisks(): Promise<Risk[]> {
  return fetchOrFallback<Risk[]>('/risks/', []);
}

export async function fetchRisk(id: string): Promise<Risk | undefined> {
  try {
    return await api.get<Risk>(`/risks/${id}/`);
  } catch (err) {
    console.error(`[DataService] GET /risks/${id} failed:`, err);
    return undefined;
  }
}

export async function createRisk(data: Partial<Risk>): Promise<Risk> {
  return api.post<Risk>('/risks/', data, { signal: AbortSignal.timeout(15000) });
}

export async function updateRisk(id: string, data: Partial<Risk>): Promise<Risk> {
  return api.put<Risk>(`/risks/${id}/`, data);
}

export async function fetchRiskControls(riskId: string): Promise<any[]> {
  try {
    return await api.get<any[]>(`/risks/${riskId}/controls`);
  } catch (err) {
    console.error(`[DataService] GET /risks/${riskId}/controls failed:`, err);
    return [];
  }
}

export async function mapControlToRisk(riskId: string, controlId: string): Promise<any> {
  return api.post<any>(`/risks/${riskId}/controls`, { control_id: controlId });
}

export async function fetchRiskCategories(): Promise<RiskCategory[]> {
  return api.get<RiskCategory[]>('/risks/categories/');
}

export function getRiskCategories(): RiskCategory[] {
  // Legacy sync function, should be replaced by fetchRiskCategories in components
  return [];
}

// -- Controls --──────
export async function fetchControls(): Promise<Control[]> {
  return fetchOrFallback<Control[]>('/controls/', []);
}

export async function createControl(data: Partial<Control>): Promise<Control> {
  return api.post<Control>('/controls/', data);
}

export async function fetchControl(id: string): Promise<Control | undefined> {
  try {
    return await api.get<Control>(`/controls/${id}/`);
  } catch (err) {
    console.error(`[DataService] GET /controls/${id} failed:`, err);
    return undefined;
  }
}

export async function updateControl(id: string, data: Partial<Control>): Promise<Control> {
  return api.patch<Control>(`/controls/${id}/`, data);
}

// -- Gap Analysis --────────
export interface GapReport {
  total_controls: number;
  applicable_controls: number;
  implemented: number;
  partially_implemented: number;
  missing: number;
  total_gaps: number;
  compliance_percentage: number;
  gaps: Array<{
    control_annex: string;
    control_title: string;
    clause_id: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    reason: string;
    current_status: string;
    best_evidence_score: number;
  }>;
  summary: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

export async function fetchGapReport(): Promise<GapReport | undefined> {
  try {
    return await api.get<GapReport>('/gap-analysis');
  } catch (err) {
    console.warn(`[DataService] GET /gap-analysis failed, building from compliance score:`, err);
    try {
      const caScore = await api.get<any>('/control-applicability/compliance-score');
      const soaRes = await api.get<any>('/control-applicability/soa').catch(() => ({ entries: [] }));
      const entries = soaRes?.entries || [];

      if (caScore) {
        const implemented = caScore.implemented ?? 0;
        const inProgress = caScore.in_progress ?? 0;
        const notStarted = caScore.not_started ?? 0;
        const notApplicable = caScore.not_applicable ?? 0;
        const total = caScore.applicable_controls || (93 - notApplicable);
        const pct = caScore.compliance_percentage ?? caScore.overall_percentage ?? 0;

        const gapsList = entries
          .filter((e: any) => e.status !== 'implemented' && e.status !== 'not_applicable')
          .map((e: any) => ({
            control_annex: e.control_annex || e.annex,
            control_title: e.control_title || e.title || `Control ${e.control_annex}`,
            clause_id: e.clause_id || e.clauseId || 'A.5',
            severity: e.status === 'not_started' ? 'critical' : 'high',
            reason: e.status === 'not_started' ? 'Control implementation not started' : 'Control partially implemented',
            current_status: e.status || 'not_started',
            best_evidence_score: 0
          }));

        return {
          total_controls: caScore.total_controls || 93,
          applicable_controls: total,
          implemented: implemented,
          partially_implemented: inProgress,
          missing: notStarted,
          total_gaps: gapsList.length,
          compliance_percentage: Math.round(pct),
          gaps: gapsList,
          summary: {
            critical: gapsList.filter((g: any) => g.severity === 'critical').length,
            high: gapsList.filter((g: any) => g.severity === 'high').length,
            medium: 0,
            low: 0
          }
        } as any;
      }
    } catch {
      // Fallback silent fail
    }
    return undefined;
  }
}

// -- Evidence --──────
export async function fetchEvidence(): Promise<Evidence[]> {
  return fetchOrFallback<Evidence[]>('/evidence/', []);
}

export async function deleteEvidence(id: string): Promise<void> {
  await api.delete(`/evidence/${id}`);
}

export async function createEvidence(data: Partial<Evidence>): Promise<Evidence> {
  return api.post<Evidence>('/evidence/', data);
}

export async function uploadEvidence(file: File, fields?: Record<string, string>): Promise<Evidence> {
  return api.upload<Evidence>('/evidence/', file, fields);
}

// -- Audit Logs --────────
export async function fetchAuditLogs(): Promise<AuditLog[]> {
  return fetchOrFallback<AuditLog[]>('/audit-logs/', []);
}

// -- Compliance --────────
export async function fetchComplianceItems(): Promise<ComplianceItem[]> {
  return fetchOrFallback<ComplianceItem[]>('/compliance/', []);
}

export async function recalculateCompliance(): Promise<any> {
  return api.post('/compliance/recalculate');
}

export interface ControlApplicabilityComplianceScore {
  total_controls: number;
  applicable_controls: number;
  implemented: number;
  in_progress: number;
  not_started: number;
  not_applicable: number;
  compliance_percentage: number;
  by_clause: Record<string, unknown>;
}

export async function fetchControlApplicabilityComplianceScore(): Promise<ControlApplicabilityComplianceScore> {
  return fetchOrFallback<ControlApplicabilityComplianceScore>('/control-applicability/compliance-score', {
    total_controls: 0,
    applicable_controls: 0,
    implemented: 0,
    in_progress: 0,
    not_started: 0,
    not_applicable: 0,
    compliance_percentage: 0,
    by_clause: {},
  });
}

export interface ControlApplicabilityInitializationResult {
  framework_id: string;
  framework_uuid?: string;
  framework_name?: string;
  initialized_count: number;
  skipped_count?: number;
  total_controls?: number;
  count: number;
  message?: string;
}

export async function initializeControlApplicability(
  organizationId: string,
  frameworkId = 'iso27001',
): Promise<ControlApplicabilityInitializationResult> {
  return api.post<ControlApplicabilityInitializationResult>('/control-applicability/initialize', {
    organization_id: organizationId,
    framework_id: frameworkId,
  });
}

export async function initializeControlApplicabilityFramework(
  frameworkId: string,
): Promise<ControlApplicabilityInitializationResult> {
  return api.post<ControlApplicabilityInitializationResult>('/control-applicability/initialize-framework', {
    framework_id: frameworkId,
  });
}

// -- Tickets --──────
export async function fetchTickets(): Promise<Ticket[]> {
  return fetchOrFallback<Ticket[]>('/tickets/', []);
}

export async function fetchTicket(id: string): Promise<Ticket | undefined> {
  try {
    return await api.get<Ticket>(`/tickets/${id}/`);
  } catch (err) {
    console.error(`[DataService] GET /tickets/${id} failed:`, err);
    return undefined;
  }
}

export async function createTicket(data: Partial<Ticket>): Promise<Ticket> {
  return api.post<Ticket>('/tickets/', data);
}

export async function updateTicket(id: string, data: Partial<Ticket>): Promise<Ticket> {
  return api.patch<Ticket>(`/tickets/${id}/`, data);
}

export async function escalateTicket(id: string, escalatedToId: string): Promise<Ticket> {
  return api.post<Ticket>(`/tickets/${id}/escalate/?escalated_to_id=${escalatedToId}`);
}

export async function resolveTicket(id: string, resolutionNotes: string): Promise<Ticket> {
  return api.post<Ticket>(`/tickets/${id}/resolve/`, { resolution_notes: resolutionNotes });
}

export async function createTicketComment(id: string, text: string): Promise<any> {
  return api.post<any>(`/tickets/${id}/comments/`, { text });
}

export async function requestEvidence(id: string, comment: string): Promise<Ticket> {
  return api.post<Ticket>(`/tickets/${id}/request-evidence/`, { comment_text: comment });
}

// -- Notifications --────────
export async function fetchNotifications(params?: { unread_only?: boolean; type?: string; limit?: number }): Promise<any[]> {
  const query = params ? `?${new URLSearchParams(params as any).toString()}` : '';
  return fetchOrFallback<any[]>('/notifications/' + query, []);
}

export async function fetchUnreadCount(): Promise<number> {
  try {
    const res = await api.get<{ count: number }>('/notifications/unread-count/');
    return res.count;
  } catch (err) {
    return 0;
  }
}

export async function markAsRead(id: string): Promise<void> {
  await api.patch(`/notifications/${id}/read/`);
}

export async function markAllRead(): Promise<void> {
  await api.patch('/notifications/mark-all-read/');
}

export async function deleteNotification(id: string): Promise<void> {
  await api.delete(`/notifications/${id}/`);
}

// -- Users --────────
export async function fetchCurrentUserProfile(): Promise<any> {
    return api.get<any>('/auth/me/');
}

export async function forgotPassword(email: string): Promise<any> {
    return api.post('/auth/forgot-password', { email }, { skipAuth: true });
}

export async function resetPassword(data: { token: string; password: string }): Promise<any> {
    return api.post('/auth/reset-password', data, { skipAuth: true });
}

export async function acceptInvite(data: { token: string; password: string }): Promise<any> {
    return api.post('/auth/accept-invite', data, { skipAuth: true });
}

export async function fetchUsers(): Promise<any[]> {
    try {
        return await api.get<any[]>('/users/');
    } catch (err) {
        console.warn(`[DataService] GET /users/ failed`, err);
        return [];
    }
}

export async function createUser(data: {
    email: string;
    full_name: string;
    password: string;
    role?: string;
    department?: string;
}): Promise<any> {
    return api.post<any>('/users/', data);
}

export async function deleteUser(userId: string): Promise<void> {
    await api.delete(`/users/${userId}`);
}

export async function updateCurrentUserProfile(data: {
    full_name?: string;
    department?: string;
}): Promise<any> {
    return api.put('/users/me', data);
}

// -- Invitations --────────
export async function inviteUser(data: {
    email: string;
    full_name: string;
    role: string;
    manager_id?: string;
    access_expires_at?: string;
}): Promise<any> {
    return api.post<any>('/invitations/invite-user', data);
}

export async function inviteAdmin(data: {
    email: string;
    full_name: string;
    organization_name: string;
}): Promise<any> {
    return api.post<any>('/invitations/invite-admin', data);
}

export async function fetchPendingInvitations(): Promise<any[]> {
    try {
        return await api.get<any[]>('/invitations/pending');
    } catch {
        return [];
    }
}

export async function cancelInvitation(userId: string): Promise<any> {
    return api.delete(`/invitations/${userId}`);
}

// -- Organization --────────
export async function fetchOrganization(): Promise<Organization | undefined> {
  try {
    return await api.get<Organization>('/organization/');
  } catch (err) {
    console.error(`[DataService] GET /organization/ failed:`, err);
    return undefined;
  }
}

export async function updateOrganization(data: Partial<Organization>): Promise<Organization> {
  return api.put<Organization>('/organization/', data);
}

export async function createOrganization(data: Partial<Organization>): Promise<Organization> {
  return api.post<Organization>('/organization/', data);
}

// -- Assets --────────
export async function fetchAssets(): Promise<Asset[]> {
  return fetchOrFallback<Asset[]>('/assets/', []);
}

export async function createAsset(data: Partial<Asset>): Promise<Asset> {
  return api.post<Asset>('/assets/', data);
}

export async function updateAsset(id: string, data: Partial<Asset>): Promise<Asset> {
  return api.put<Asset>(`/assets/${id}/`, data);
}

export async function deleteAsset(id: string): Promise<void> {
  return api.delete(`/assets/${id}/`);
}

export async function linkRiskToAsset(assetId: string, riskId: string): Promise<any> {
  return api.post<any>(`/assets/${assetId}/risks`, { risk_id: riskId });
}

export async function unlinkRiskFromAsset(assetId: string, riskId: string): Promise<void> {
  return api.delete(`/assets/${assetId}/risks/${riskId}`);
}

// -- Audit Preparation --────────
export async function fetchReadinessScore(orgId: string): Promise<any> {
  return fetchOrFallback<any>(`/audit-preparation/readiness?organization_id=${orgId}`, {
    compliance_percentage: 0,
    weighted_readiness: 0,
    total_controls: 0,
    implemented_controls: 0,
    critical_gaps: 0,
    high_gaps: 0
  });
}

async function downloadExport(endpoint: string, fallbackFilename: string): Promise<Blob> {
  const url = `${api.baseUrl}${endpoint}`;
  
  // Custom fetch needed for Blob handling
  const { data: { session } } = await supabase.auth.getSession();
  const headers: Record<string, string> = {};
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error('Export failed');
  return response.blob();
}

export async function exportAuditReport(orgId: string, format: 'pdf' | 'csv' = 'pdf'): Promise<Blob> {
  return downloadExport(`/audit-preparation/export/?organization_id=${orgId}&format=${format}`, 'Audit_Report');
}

export async function exportSoAReport(orgId: string, format: 'pdf' | 'csv' = 'pdf'): Promise<Blob> {
  return downloadExport(`/audit-preparation/soa/export/?organization_id=${orgId}&format=${format}`, 'ISO27001_SoA');
}

export async function exportRiskRegister(orgId: string, format: 'pdf' | 'csv' = 'pdf'): Promise<Blob> {
  return downloadExport(`/audit-preparation/risk-register/export/?organization_id=${orgId}&format=${format}`, 'Risk_Register');
}

// -- Document Analysis --────────
export async function fetchDocumentAnalyses(): Promise<DocumentAnalysis[]> {
  return fetchOrFallback<DocumentAnalysis[]>('/document-analysis/', []);
}

export async function submitDocumentForAnalysis(file: File, organizationId?: string): Promise<DocumentAnalysis> {
  return api.upload<DocumentAnalysis>('/document-analysis/upload/', file, { 
    ...(organizationId && { organization_id: organizationId }),
    link_as_evidence: 'false'
  });
}
// -- Dashboard --────────
export interface DashboardSummary {
  risk_stats: {
    total: number;
    high_risk: number;
    mitigated: number;
  };
  control_stats: {
    total: number;
    implemented: number;
    effectiveness_avg: number;
  };
  compliance_stats: {
    overall_percentage: number;
    total_frameworks: number;
  };
  recent_activity: AuditLog[];
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const empty: DashboardSummary = {
    risk_stats: { total: 0, high_risk: 0, mitigated: 0 },
    control_stats: { total: 0, implemented: 0, effectiveness_avg: 0 },
    compliance_stats: { overall_percentage: 0, total_frameworks: 0 },
    recent_activity: []
  };

  return fetchOrFallback<DashboardSummary>('/dashboard/summary/', empty);
}

// -- Permission Profiles --────────
export interface PermissionProfile {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  nav_permissions: Record<string, boolean>;
  created_at: string;
  updated_at: string;
}

export async function fetchPermissionProfiles(): Promise<PermissionProfile[]> {
  return fetchOrFallback<PermissionProfile[]>('/permission-profiles/', []);
}

export async function createPermissionProfile(data: {
  name: string;
  description?: string;
  nav_permissions: Record<string, boolean>;
}): Promise<PermissionProfile> {
  return api.post<PermissionProfile>('/permission-profiles/', data);
}

export async function updatePermissionProfile(
  id: string,
  data: { name?: string; description?: string; nav_permissions?: Record<string, boolean> }
): Promise<PermissionProfile> {
  return api.put<PermissionProfile>(`/permission-profiles/${id}`, data);
}

export async function deletePermissionProfile(id: string): Promise<any> {
  return api.delete(`/permission-profiles/${id}`);
}

export async function assignPermissionProfile(data: {
  user_id: string;
  permission_profile_id?: string | null;
}): Promise<any> {
  return api.post('/permission-profiles/assign', data);
}

