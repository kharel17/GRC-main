/**
 * GRC Platform — Data Service
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
  mockUsers,
} from './mock-data';
import type { Risk, RiskCategory } from '@/types/risk';
import type { Control } from '@/types/control';
import type { ComplianceItem } from '@/types/compliance';
import type { Evidence } from '@/types/evidence';
import type { AuditLog } from '@/types/audit';
import type { Ticket } from '@/types/ticket';
import type { UserProfile } from '@/types/user';

// ── Helper ─────────────────────────────────────────────────
async function fetchOrFallback<T>(endpoint: string, fallback: T): Promise<T> {
  if (api.isMock) return fallback;
  try {
    return await api.get<T>(endpoint);
  } catch (err) {
    console.warn(`[DataService] API call ${endpoint} failed, using mock data`, err);
    return fallback;
  }
}

// ── Risk ───────────────────────────────────────────────────
export async function fetchRisks(): Promise<Risk[]> {
  return fetchOrFallback<Risk[]>('/risks', mockRisks);
}

export async function fetchRisk(id: string): Promise<Risk | undefined> {
  if (api.isMock) return mockRisks.find((r) => r.id === id);
  try {
    return await api.get<Risk>(`/risks/${id}`);
  } catch (err) {
    console.warn(`[DataService] GET /risks/${id} failed, using mock`, err);
    return mockRisks.find((r) => r.id === id);
  }
}

export async function createRisk(data: Partial<Risk>): Promise<Risk> {
  return api.post<Risk>('/risks', data);
}

export function getRiskCategories(): RiskCategory[] {
  // Categories are small and rarely change — keep local until a backend
  // endpoint exists for them.
  return mockRiskCategories;
}

// ── Controls ───────────────────────────────────────────────
export async function fetchControls(): Promise<Control[]> {
  return fetchOrFallback<Control[]>('/controls', mockControls);
}

export async function createControl(data: Partial<Control>): Promise<Control> {
  return api.post<Control>('/controls', data);
}

// ── Evidence ───────────────────────────────────────────────
export async function fetchEvidence(): Promise<Evidence[]> {
  return fetchOrFallback<Evidence[]>('/evidence', mockEvidence);
}

export async function createEvidence(data: Partial<Evidence>): Promise<Evidence> {
  return api.post<Evidence>('/evidence', data);
}

export async function uploadEvidence(file: File, fields?: Record<string, string>): Promise<Evidence> {
  return api.upload<Evidence>('/evidence/upload', file, fields);
}

// ── Audit Logs ─────────────────────────────────────────────
export async function fetchAuditLogs(): Promise<AuditLog[]> {
  return fetchOrFallback<AuditLog[]>('/audit-logs', mockAuditLogs);
}

// ── Compliance ─────────────────────────────────────────────
export async function fetchComplianceItems(): Promise<ComplianceItem[]> {
  return fetchOrFallback<ComplianceItem[]>('/compliance', mockComplianceItems);
}

// ── Tickets ────────────────────────────────────────────────
export async function fetchTickets(): Promise<Ticket[]> {
  return fetchOrFallback<Ticket[]>('/tickets', mockTickets);
}

export async function fetchTicket(id: string): Promise<Ticket | undefined> {
  if (api.isMock) return mockTickets.find((t) => t.id === id);
  try {
    return await api.get<Ticket>(`/tickets/${id}`);
  } catch (err) {
    console.warn(`[DataService] GET /tickets/${id} failed, using mock`, err);
    return mockTickets.find((t) => t.id === id);
  }
}

export async function createTicket(data: Partial<Ticket>): Promise<Ticket> {
  return api.post<Ticket>('/tickets', data);
}

export async function updateTicket(id: string, data: Partial<Ticket>): Promise<Ticket> {
  return api.put<Ticket>(`/tickets/${id}`, data);
}

// ── Users ──────────────────────────────────────────────────
export async function fetchUsers(): Promise<UserProfile[]> {
  const users = await fetchOrFallback<any[]>('/users', mockUsers);
  // Map snake_case from API to camelCase for frontend if needed, 
  // but schemas seem to use snake_case often in this codebase.
  // Actually, UserProfile type uses camelCase.
  return users.map(u => ({
    id: u.id,
    email: u.email,
    fullName: u.full_name || u.fullName,
    role: u.role,
    department: u.department,
    is_active: u.is_active ?? true,
    createdAt: u.created_at || u.createdAt,
    updatedAt: u.updated_at || u.updatedAt,
  }));
}

export async function createUser(data: any): Promise<UserProfile> {
  return api.post<UserProfile>('/users', data);
}

export async function updateUser(id: string, data: any): Promise<UserProfile> {
  return api.put<UserProfile>(`/users/${id}`, data);
}

export async function deleteUser(id: string): Promise<void> {
  await api.delete(`/users/${id}`);
}
