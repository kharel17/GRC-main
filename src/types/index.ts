export type UserRole = 
  | 'superadmin' 
  | 'admin' 
  | 'manager' 
  | 'analyst' 
  | 'control_owner' 
  | 'risk_owner' 
  | 'compliance_officer' 
  | 'department_manager' 
  | 'executive' 
  | 'auditor'

export interface PermissionProfile {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  nav_permissions: Record<string, boolean>;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  organization_id: string
  organization_name?: string
  manager_id?: string
  permission_profile_id?: string
  permission_profile?: PermissionProfile
  invitation_status: string
  is_acting_admin: boolean
  created_at: string
}

export interface UserProfile {
  id: string
  email: string
  full_name: string
  fullName?: string // alias
  role: UserRole
  organization_id: string
  organization_name?: string
  manager_id?: string
  permission_profile_id?: string
  permission_profile?: PermissionProfile
  invitation_status: string
  is_acting_admin: boolean
  department?: string
  createdAt?: string // alias
  updatedAt?: string // alias
}

export interface Organization {
  id: string
  name: string
  industry?: string
  employee_count?: string
  infrastructure?: string
  data_types?: string
  onboarding_completed?: boolean
  description?: string
  size?: string
  website?: string
  country?: string
  compliance_target_date?: string
  isms_scope?: string
  primaryContactId?: string
  complianceFrameworks?: string[]
  compliance_frameworks?: string[]
  created_at?: string
  createdAt?: string // alias
  updated_at?: string
  updatedAt?: string // alias
}

export type RiskStatus = 
  | 'open' | 'in_progress' | 'resolved'
  | 'identified' | 'assessed' | 'mitigated' | 'accepted' | string

export type RiskSeverity = 1 | 2 | 3 | 4 | 5

export interface RiskCategory {
  id: string
  name: string
  description?: string
  color: string
}

export interface Risk {
  id: string
  title: string
  description: string
  probability?: number
  likelihood: RiskSeverity
  impact: RiskSeverity
  score: number
  riskScore?: number // alias
  risk_score?: number // alias
  owner_id?: string
  ownerId?: string // alias
  organization_id?: string
  organizationId?: string // alias
  status: RiskStatus
  category?: RiskCategory
  categoryId?: string
  category_id?: string // alias
  primaryContactId?: string
  ownerName?: string
  createdBy?: string // alias
  created_at?: string
  createdAt?: string // alias
  updated_at?: string
  updatedAt?: string // alias
}

export type ControlType = 
  | 'Technical' | 'Administrative' | 'Physical'
  | 'preventive' | 'detective' | 'corrective'

export type ControlStatus = 
  | 'Implemented' | 'Partial' | 'Not Implemented'
  | 'planned' | 'implemented' | 'under_review' | string

export interface Control {
  id: string
  title: string
  description?: string
  type?: ControlType
  control_type?: 'preventive' | 'detective' | 'corrective' | string
  controlType?: ControlType // alias
  iso_clause?: string
  effectiveness?: number | 'high' | 'medium' | 'low' | string
  owner_id?: string
  ownerId?: string // alias
  ownerName?: string // alias
  linked_risk_id?: string
  organization_id?: string
  organizationId?: string // alias
  status?: ControlStatus
  created_at?: string
  createdAt?: string // alias
  updated_at?: string
  updatedAt?: string // alias
  createdBy?: string // alias
}

export interface ComplianceItem {
  id: string
  title?: string
  description?: string
  framework?: string
  requirementId?: string
  dueDate?: string
  control_id?: string
  iso_clause?: string
  status: string
  priority?: ComplianceItemPriority
  priority_score?: number
  ownerId?: string // alias
  ownerName?: string // alias
  created_at?: string
  createdAt?: string // alias
  updated_at?: string
  updatedAt?: string // alias
  evidenceCount?: number // alias
}

export type ComplianceItemPriority = 'critical' | 'high' | 'medium' | 'low' | string

export type EvidenceStatus = 
  'submitted' | 'under_review' | 'pending' |
  'verified' | 'rejected' | 'expired' | 'active'

export interface Evidence {
  id: string
  title: string
  description?: string
  file_path: string
  file_name: string
  fileName?: string // alias
  file_url?: string
  fileUrl?: string // alias
  file_type?: string
  fileType?: string // alias
  file_size?: number
  fileSize?: number // alias
  control_id?: string
  uploaded_by: string
  uploadedByName?: string // alias
  uploaded_at: string
  confidence_score: number
  ai_summary?: string
  matched_iso_clause?: string
  status: EvidenceStatus
  valid_until?: string
  verified?: boolean
  verified_by?: string
  verified_by_name?: string // alias
  verifiedByName?: string // alias
  verified_at?: string
  verifiedBy?: string // alias
  verifiedAt?: string // alias
  uploadedBy?: string // alias
  uploadedAt?: string // alias
  related_to?: string
  relatedTo?: string // alias
  relatedName?: string // alias
  related_id?: string
  relatedId?: string // alias
  organization_id?: string
  created_at?: string
  createdAt?: string // alias
}

export interface AuditLog {
  id: string
  action: string
  actor_id: string
  target_id?: string
  targetId?: string // alias
  userId?: string // alias
  meta: Record<string, unknown>
  entityType?: string
  entityId?: string // alias
  entityName?: string
  description?: string
  userName?: string
  timestamp?: string
  oldValues?: Record<string, unknown> | null;
  newValues?: Record<string, unknown> | null;
  ipAddress?: string
  created_at?: string
  createdAt?: string // alias
}

export type Criticality = 
  | 'Critical' | 'High' | 'Medium' | 'Low'
  | 'critical' | 'high' | 'medium' | 'low'

export type TicketStatus = 
  | 'open' | 'in_review' | 'pending_evidence' | 'escalated' | 'resolved' | 'closed'
  | 'overdue' | 'pending_l2_review' | 'pending_l1_signoff' | 'archived' | 'rejected' | string

export type TicketPriority = 'critical' | 'high' | 'medium' | 'low' | string
export type TicketCategory = string
export type EscalationLevel = 1 | 2 | 3 | 4 | number

export interface TicketComment {
  id: string
  text: string
  authorId: string
  authorName: string
  authorRole: string
  timestamp: string
}

export interface TicketActivity {
  id: string
  activityType: string
  description: string
  timestamp: string
  userId: string
  oldValue?: string
  newValue?: string
}

export interface Ticket {
  id: string
  title: string
  description: string
  iso_clause?: string
  isoClause?: string // alias
  weight_score?: number
  riskScore?: number // alias
  criticality?: Criticality
  priority: TicketPriority
  category: TicketCategory
  status: TicketStatus
  assigned_to?: string
  assignedToId?: string
  assignedToName?: string
  assignedToRole?: string
  managerId?: string
  escalatedToRole?: string
  escalatedToId?: string
  escalatedToName?: string
  escalated_at?: string
  escalatedAt?: string // alias
  resolved_at?: string
  resolvedAt?: string // alias
  status_updated_at?: string
  statusUpdatedAt?: string // alias
  createdBy?: string
  creatorName?: string
  organization_id?: string
  organizationId?: string // alias
  due_date?: string
  dueDate?: string // alias
  is_repeat_finding?: boolean
  isRepeatFinding?: boolean // alias
  previousTicketId?: string
  is_auto_escalation_enabled?: boolean
  isAutoEscalationEnabled?: boolean // alias
  escalationLevel?: EscalationLevel
  comments: TicketComment[]
  activities: TicketActivity[]
  relatedRiskId?: string
  relatedEntityType?: string
  relatedEntityId?: string
  sourceAuditLogId?: string // alias
  source_audit_log_id?: string // alias
  resolutionNotes?: string // alias
  created_at?: string
  createdAt?: string // alias
  updated_at?: string
  updatedAt?: string // alias
}

export type AssetType = string
export type AssetCriticality = Criticality
export type AssetClassification = 
  | 'Public' | 'Internal' | 'Confidential' | 'Secret'
  | 'public' | 'internal' | 'confidential' | 'secret' | 'restricted'

export interface Asset {
  id: string
  name: string
  description?: string
  type?: AssetType
  criticality?: AssetCriticality
  classification?: AssetClassification
  location?: string
  status?: string
  owner_id?: string
  ownerId?: string // alias
  organization_id?: string
  organizationId?: string // alias
  related_risks?: string[]
  created_at?: string
  createdAt?: string // alias
  updated_at?: string
  updatedAt?: string // alias
  assetType?: string // alias
}

export type AssetStatus = 'active' | 'maintenance' | 'retired' | string

export * from './iso27001'

export interface DocumentAnalysis {
  id: string
  organization_id?: string
  organizationId?: string // alias
  file_name?: string
  document_name?: string
  fileName?: string // alias
  status?: string
  documentCategory?: string
  analyzedAt?: string
  iso_clauses?: string[]
  confidence_score?: number
  findings?: Array<{
    clause: string
    finding: string
    action: string
    severity: 'high' | 'medium' | 'low'
  }>
  implemented_controls?: Array<{
    annex: string
    title: string
    evidence_found?: string
  }>
  missing_controls?: Array<{
    annex: string
    title: string
    reason?: string
  }>
  summary?: string
  created_at?: string
  createdAt?: string // alias
}

export interface Notification {
  id: string
  user_id: string
  ticket_id: string
  message: string
  type: string
  is_read: boolean
  created_at: string
}

export interface ApiError {
  code: string
  message: string
  status: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}
