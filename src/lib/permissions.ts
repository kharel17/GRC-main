import { UserRole } from '@/types';

export const PERMISSIONS: Record<string, UserRole[]> = {
  // Assets
  CREATE_ASSET: ['admin', 'manager'],
  EDIT_ASSET: ['admin', 'manager'],
  DELETE_ASSET: ['admin'],
  VIEW_ASSETS: ['admin', 'manager', 'analyst'],
  
  // Risks
  CREATE_RISK: ['admin', 'manager'],
  EDIT_RISK: ['admin', 'manager'],
  DELETE_RISK: ['admin'],
  VIEW_RISKS: ['admin', 'manager', 'analyst'],
  
  // Controls
  CREATE_CONTROL: ['admin', 'manager'],
  EDIT_CONTROL: ['admin', 'manager'],
  DELETE_CONTROL: ['admin'],
  VIEW_CONTROLS: ['admin', 'manager', 'analyst'],
  MAP_CONTROL_TO_RISK: ['admin', 'manager', 'analyst'],
  
  // Evidence
  UPLOAD_EVIDENCE: ['admin', 'manager', 'analyst'],
  VIEW_EVIDENCE: ['admin', 'manager', 'analyst'],
  DELETE_EVIDENCE: ['admin', 'manager', 'analyst'], // Analyst restricted in backend
  VERIFY_EVIDENCE: ['admin', 'manager'],
  REJECT_EVIDENCE: ['admin', 'manager'],
  
  // Document Analysis
  UPLOAD_DOCUMENT: ['admin', 'manager', 'analyst'],
  VIEW_DOCUMENT_ANALYSIS: ['admin', 'manager', 'analyst'],
  REGENERATE_ANALYSIS: ['admin', 'manager', 'analyst'],
  
  // Gap Analysis
  VIEW_GAP_ANALYSIS: ['admin', 'manager', 'analyst'],
  REGENERATE_GAP: ['admin', 'manager', 'analyst'],
  
  // Reports
  VIEW_REPORTS: ['admin', 'manager', 'analyst'],
  GENERATE_REPORTS: ['admin', 'manager', 'analyst'],
  DOWNLOAD_REPORTS: ['admin', 'manager', 'analyst'],
  
  // Tickets
  VIEW_TICKETS: ['admin', 'manager', 'analyst'], // Analyst only sees own
  RESOLVE_TICKET: ['admin', 'manager', 'analyst'],
  APPROVE_TICKET: ['admin', 'manager'],
  REJECT_TICKET: ['admin', 'manager'],
  CLOSE_TICKET: ['admin'],
  
  // Users
  VIEW_USERS: ['admin', 'manager'],
  INVITE_USER: ['admin', 'manager'], // Manager can only invite Analysts (logic in component)
  DELETE_USER: ['admin'],
  
  // Organization
  VIEW_ORG: ['admin', 'manager'],
  EDIT_ORG: ['admin'],
  
  // Audit Log
  VIEW_AUDIT_LOG: ['admin', 'manager'],
  
  // Audit Prep
  VIEW_AUDIT_PREP: ['admin', 'manager', 'analyst'],
};
