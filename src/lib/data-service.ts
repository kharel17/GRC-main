/**
 * GRC Platform - Data Service
 *
 * Centralized data fetching: calls the real FastAPI backend when available,
 * gracefully falls back to mock data when the API is unreachable or when
 * NEXT_PUBLIC_USE_MOCK=true.
 *
 * Every page should use the functions here instead of importing mock arrays
 * directly.
 */

import { api } from './api-client';
import { supabase } from './supabase';
import {
  mockRisks,
  mockRiskCategories,
  mockControls,
  mockComplianceItems,
  mockEvidence,
  mockAuditLogs,
  mockTickets,
  mockOrganization,
  mockAssets,
  mockDocumentAnalyses,
} from './mock-data';
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
  if (api.isMock) return fallback;
  try {
    return await api.get<T>(endpoint);
  } catch (err) {
    console.error(`[DataService] API call ${endpoint} failed:`, err);
    // In production, do not fall back to rich mock data. Return empty array/undefined.
    return (Array.isArray(fallback) ? [] : undefined) as unknown as T;
  }
}

// -- Risk --────────
export async function fetchRisks(): Promise<Risk[]> {
  return fetchOrFallback<Risk[]>('/risks/', mockRisks);
}

export async function fetchRisk(id: string): Promise<Risk | undefined> {
  if (api.isMock) return mockRisks.find((r) => r.id === id);
  try {
    return await api.get<Risk>(`/risks/${id}/`);
  } catch (err) {
    console.error(`[DataService] GET /risks/${id} failed:`, err);
    return undefined;
  }
}

export async function createRisk(data: Partial<Risk>): Promise<Risk> {
  return api.post<Risk>('/risks/', data);
}

export async function updateRisk(id: string, data: Partial<Risk>): Promise<Risk> {
  return api.put<Risk>(`/risks/${id}/`, data);
}

export async function fetchRiskControls(riskId: string): Promise<any[]> {
  try {
    return await api.get<any[]>(`/risks/${riskId}/controls/`);
  } catch (err) {
    console.error(`[DataService] GET /risks/${riskId}/controls failed:`, err);
    return [];
  }
}

export async function mapControlToRisk(riskId: string, controlId: string): Promise<any> {
  return api.post<any>(`/risks/${riskId}/controls/`, { control_id: controlId });
}

export function getRiskCategories(): RiskCategory[] {
  // Categories are small and rarely change - keep local until a backend
  // endpoint exists for them.
  return mockRiskCategories;
}

// -- Controls --──────
export async function fetchControls(): Promise<Control[]> {
  return fetchOrFallback<Control[]>('/controls/', mockControls);
}

export async function createControl(data: Partial<Control>): Promise<Control> {
  return api.post<Control>('/controls/', data);
}

export async function fetchControl(id: string): Promise<Control | undefined> {
  if (api.isMock) return mockControls.find((c) => c.id === id);
  try {
    return await api.get<Control>(`/controls/${id}/`);
  } catch (err) {
    console.error(`[DataService] GET /controls/${id} failed:`, err);
    return undefined;
  }
}

export async function updateControl(id: string, data: Partial<Control>): Promise<Control> {
  return api.put<Control>(`/controls/${id}/`, data);
}

// -- Evidence --──────
export async function fetchEvidence(): Promise<Evidence[]> {
  return fetchOrFallback<Evidence[]>('/evidence/', mockEvidence);
}

export async function createEvidence(data: Partial<Evidence>): Promise<Evidence> {
  return api.post<Evidence>('/evidence/', data);
}

export async function uploadEvidence(file: File, fields?: Record<string, string>): Promise<Evidence> {
  return api.upload<Evidence>('/evidence/upload/', file, fields);
}

// -- Audit Logs --────────
export async function fetchAuditLogs(): Promise<AuditLog[]> {
  return fetchOrFallback<AuditLog[]>('/audit-logs/', mockAuditLogs);
}

// -- Compliance --────────
export async function fetchComplianceItems(): Promise<ComplianceItem[]> {
  return fetchOrFallback<ComplianceItem[]>('/compliance/', mockComplianceItems);
}

// -- Tickets --──────
export async function fetchTickets(): Promise<Ticket[]> {
  return fetchOrFallback<Ticket[]>('/tickets/', mockTickets);
}

export async function fetchTicket(id: string): Promise<Ticket | undefined> {
  if (api.isMock) return mockTickets.find((t) => t.id === id);
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
  return api.put<Ticket>(`/tickets/${id}/`, data);
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
export async function fetchNotifications(): Promise<any[]> {
  return fetchOrFallback<any[]>('/notifications/', []);
}

export async function fetchUnreadCount(): Promise<number> {
  try {
    const res = await api.get<{ count: number }>('/notifications/unread-count/');
    return res.count;
  } catch (err) {
    return 0;
  }
}

export async function markAllRead(): Promise<void> {
  await api.post('/notifications/mark-all-read/');
}

// -- Users --────────
export async function fetchCurrentUserProfile(): Promise<any> {
  return api.get<any>('/auth/me/');
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
  manager_id?: string;
  is_acting_admin?: number;
}): Promise<any> {
  return api.post<any>('/users/', data);
}

// -- Invitations --────────
export async function inviteUser(data: {
  email: string;
  full_name: string;
  role: string;
  manager_id?: string;
}): Promise<any> {
  return api.post<any>('/invitations/invite-user/', data);
}

export async function inviteAdmin(data: {
  email: string;
  full_name: string;
  organization_name: string;
}): Promise<any> {
  return api.post<any>('/invitations/invite-admin/', data);
}

export async function fetchPendingInvitations(): Promise<any[]> {
  try {
    return await api.get<any[]>('/invitations/pending/');
  } catch {
    return [];
  }
}

export async function cancelInvitation(userId: string): Promise<any> {
  return api.delete(`/invitations/${userId}/`);
}

// -- Organization --────────
export async function fetchOrganization(): Promise<Organization | undefined> {
  return fetchOrFallback<Organization | undefined>('/organizations/', mockOrganization);
}

export async function updateOrganization(id: string, data: Partial<Organization>): Promise<Organization> {
  return api.put<Organization>(`/organizations/${id}/`, data);
}

// -- Assets --────────
export async function fetchAssets(): Promise<Asset[]> {
  return fetchOrFallback<Asset[]>('/assets/', mockAssets);
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
  return api.post<any>(`/assets/${assetId}/risks/`, { risk_id: riskId });
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
  return downloadExport(`/audit-preparation/export?organization_id=${orgId}&format=${format}`, 'Audit_Report');
}

export async function exportSoAReport(orgId: string, format: 'pdf' | 'csv' = 'pdf'): Promise<Blob> {
  return downloadExport(`/audit-preparation/soa/export?organization_id=${orgId}&format=${format}`, 'ISO27001_SoA');
}

export async function exportRiskRegister(orgId: string, format: 'pdf' | 'csv' = 'pdf'): Promise<Blob> {
  return downloadExport(`/audit-preparation/risk-register/export?organization_id=${orgId}&format=${format}`, 'Risk_Register');
}

// -- Document Analysis --────────
export async function fetchDocumentAnalyses(): Promise<DocumentAnalysis[]> {
  return fetchOrFallback<DocumentAnalysis[]>('/document-analysis/', mockDocumentAnalyses);
}

export async function submitDocumentForAnalysis(file: File): Promise<DocumentAnalysis> {
  return api.upload<DocumentAnalysis>('/document-analysis/upload/', file);
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
  const fallback: DashboardSummary = {
    risk_stats: { total: mockRisks.length, high_risk: mockRisks.filter(r => r.riskScore > 15).length, mitigated: mockRisks.filter(r => r.status === 'mitigated').length },
    control_stats: { total: mockControls.length, implemented: mockControls.filter(c => c.status === 'implemented').length, effectiveness_avg: 85 },
    compliance_stats: { overall_percentage: 72, total_frameworks: 1 },
    recent_activity: mockAuditLogs.slice(0, 5)
  };

  return fetchOrFallback<DashboardSummary>('/dashboard/summary/', fallback);
}
