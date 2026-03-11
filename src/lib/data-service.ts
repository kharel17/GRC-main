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
import {
  mockRisks,
  mockRiskCategories,
  mockControls,
  mockComplianceItems,
  mockEvidence,
  mockAuditLogs,
  mockTickets,
} from './mock-data';
import type { Risk, RiskCategory } from '@/types/risk';
import type { Control } from '@/types/control';
import type { ComplianceItem } from '@/types/compliance';
import type { Evidence } from '@/types/evidence';
import type { AuditLog } from '@/types/audit';
import type { Ticket } from '@/types/ticket';

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
    return await api.get<any[]>(`/risks/${riskId}/controls`);
  } catch (err) {
    console.error(`[DataService] GET /risks/${riskId}/controls failed:`, err);
    return [];
  }
}

export async function mapControlToRisk(riskId: string, controlId: string): Promise<any> {
  return api.post<any>(`/risks/${riskId}/controls`, { control_id: controlId });
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

// -- Evidence --──────
export async function fetchEvidence(): Promise<Evidence[]> {
  return fetchOrFallback<Evidence[]>('/evidence/', mockEvidence);
}

export async function createEvidence(data: Partial<Evidence>): Promise<Evidence> {
  return api.post<Evidence>('/evidence/', data);
}

export async function uploadEvidence(file: File, fields?: Record<string, string>): Promise<Evidence> {
  return api.upload<Evidence>('/evidence/upload', file, fields);
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

// -- Users --────────
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
