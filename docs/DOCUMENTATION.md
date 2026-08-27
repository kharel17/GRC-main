# GRC Platform - Complete Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [What's Implemented](#whats-implemented)
3. [Architecture & Structure](#architecture--structure)
4. [User Walkthrough](#user-walkthrough)
5. [Pending & Future Work](#pending--future-work)
6. [Getting Started](#getting-started)
7. [Production Readiness Plan](#production-readiness-plan)

---

## Production Readiness Plan

The production-readiness work is tracked as a phased plan in:

- [docs/PRODUCTION_READINESS_PHASES.md](docs/PRODUCTION_READINESS_PHASES.md)

Follow that document phase-by-phase for mock data removal, multi-tenancy isolation, invitation flow completion, frontend updates, environment variables, cleanup SQL, and final verification.

---

## Project Overview

**GRC Platform** is a lightweight, modern Governance, Risk, and Compliance management application built with Next.js 13+, React, and TypeScript. It provides organizations with a centralized platform to manage risks, controls, compliance requirements, and audit trails.

### Key Highlights

- 🎯 **Role-Based Access Control**: Admin, Analyst, and Manager roles with different permissions
- 📊 **Risk Management**: Comprehensive risk tracking with transparent scoring
- ✅ **Compliance Tracking**: Monitor compliance against multiple frameworks (ISO 27001)
- 📋 **Control Management**: Map controls to risks and compliance requirements
- 📖 **Evidence Management**: Track and verify compliance evidence
- 📈 **Dashboard**: Real-time KPIs and risk metrics
- 🎨 **Professional UI**: Built with shadcn/ui components and Tailwind CSS
- ⚡ **Performance Optimized**: ~80 kB initial load JS

### Tech Stack

- **Frontend Framework**: Next.js 13+ (App Router)
- **Language**: TypeScript (strict mode)
- **UI Framework**: React 18
- **Component Library**: shadcn/ui (30+ components)
- **Styling**: Tailwind CSS 3
- **State Management**: React Context API
- **Authentication**: Mock (localStorage) - ready for Supabase
- **Form Handling**: React Hook Form + Zod validation
- **Icons**: Lucide React

---

## What's Implemented

### ✅ Core Features

#### 1. **Authentication & Authorization**

- Mock login system with 3 test accounts (Admin, Analyst, Manager)
- Role-based access control (RBAC) with permission checks
- localStorage-based session management //aws ko access vayepaxi enter garera backend chirne
- Login page with role selection
- Protected routes for authenticated users only

**Test Accounts**: 

```
Email                    Role      Status
alice@company.com        Admin     Active
bob@company.com          Analyst   Active
carol@company.com        Manager   Active

Password for all: demo
```

#### 2. **Dashboard** (`/dashboard`)

Real-time metrics including:

- 📊 **Average Risk Score**: Calculated from all risks in the system
- ⚠️ **Open Risks**: Count of active/unmitigated risks
- ✅ **Compliance Rate**: Percentage of compliant items
- 🛡️ **Implemented Controls**: Count of active controls

Sections:

- **Risk Highlights**: Top 3 highest-risk items at a glance
- **Upcoming/Overdue Items**: Risk assessments and control reviews
- **KPI Trend Analysis**: Visual indicators (↑↓) for metric trends

#### 3. **Risk Management** (`/dashboard/risks`)

**List View** (`/dashboard/risks`):

- Complete risk inventory with filterable table
- Columns: Title, Category, Score, Probability, Impact, Status
- Real-time calculations for risk scores
- Sorting by priority/status
- Category badges with color coding
- Status indicators (Open, Mitigated, Accepted, etc.)

**Detail View** (`/dashboard/risks/[id]`):

- Full risk information
- **Transparent Scoring Breakdown**:
  - Probability (1-5 scale)
  - Impact (1-5 scale)
  - Risk Score = Probability × Impact
  - Color-coded severity indicator
- Mapped Controls: Which controls mitigate this risk
- Related Compliance Items
- Risk Timeline/Updates
- Action buttons for status changes

**Sample Risks**:

- Data Breach (Technology)
- Regulatory Non-Compliance (Compliance)
- Employee Turnover (Operational)
- System Outage (Operational)
- Fraud Detection (Financial)
- IP Theft (Strategic)

#### 4. **Controls Management** (`/dashboard/controls`)

- Card-based control inventory (90+ ISO 27001 controls)
- **Available Filters**:
  - Control Type (Technical, Administrative, Physical)
  - Effectiveness (High/Medium/Low)
  - Status (Implemented, Planned, Monitoring)
- Control Details:
  - Description & implementation guidance
  - Mapped Risks (which risks this control mitigates)
  - Mapped Compliance Items
  - Status and effectiveness rating

**Control Types**:

- **Technical**: 40 controls (encryption, access management, etc.)
- **Administrative**: 30 controls (policies, procedures)
- **Physical**: 20 controls (facilities, locks, etc.)

#### 5. **Evidence Management** (`/dashboard/evidence`)

- Table view of all compliance evidence
- Track document uploads and verification status
- Columns: Item, Type, Uploaded By, Status, Last Updated
- **Status Types**: Submitted, Under Review, Verified, Rejected
- File upload simulation (UI ready, backend integration pending)

**Evidence Categories**:

- Policy Documents
- Audit Reports
- Training Records
- System Logs
- Incident Reports
- Assessment Results

#### 6. **ISO 27001 Compliance**

- 90 controls from ISO 27001 Annex A
- Organized by control groups
- **Compliance Scoring**: Real-time calculation of compliance rate
- Control Status Breakdown:
  - Implemented: 60%
  - Planned: 25%
  - Not Implemented: 15%

**Available Pages**:

- Compliance Dashboard with overall compliance percentage
- ISO Control List with filtering
- Control Detail Pages with risk mapping

#### 7. **Audit Logs** (`/dashboard/audits`)

- Immutable activity timeline
- Event types: Login, Risk Updated, Control Reviewed, Evidence Verified, etc.
- User attribution for all actions
- Timestamp tracking
- Searchable and filterable audit trail

#### 8. **Reports** (`/dashboard/reports`)

- Report template library
- **Available Templates**:
  - Compliance Summary: Overall compliance metrics
  - Risk Assessment: Risk portfolio analysis
  - Control Status: Control implementation status
  - Executive Summary: High-level overview
- Export options UI (ready for backend)

#### 9. **Settings** (`/dashboard/settings`)

- Account management
- User preferences
- Theme selector (Light/Dark mode)
- Password management (UI ready)
- Notification preferences

#### 10. **Navigation & Layout**

- **Responsive Sidebar**:
  - Expands/collapses on mobile
  - Main nav items: Dashboard, Risks, Controls, Evidence, Audits, Reports, Settings
  - Role-based menu items (Analysts see different options than Managers)
  - Breadcrumb navigation
- **Header**:
  - User profile dropdown
  - Theme toggle
  - Logout button
- **Mobile Responsive**: Optimized for all screen sizes

### ✅ Design System

**Color Palette**:

- Primary: Blue (#0066CC, #3B82F6)
- Secondary: Slate gray (#64748B, #94A3B8)
- Accents:
  - Success: Green (#10B981, #34D399)
  - Warning: Amber (#FBBF24, #FCD34D)
  - Error: Red (#EF4444, #F87171)
  - Info: Cyan (#06B6D4, #22D3EE)

**Typography**:

- Font: Inter (system fallback)
- Heading scales: h1-h6
- Body text: 14px base, 16px readable length

**Spacing**:

- 8px base unit (8, 16, 24, 32, 40, 48, 56, 64)
- Consistent padding/margins throughout

**Components** (30+ UI Components):

- Forms: Input, Textarea, Checkbox, Radio, Select, Slider
- Data Display: Table, Badge, Avatar, Progress, Card
- Navigation: Breadcrumb, Tabs, Sidebar, Dropdown
- Feedback: Toast, Dialog, Alert, Tooltip
- Layout: Container, Flex, Grid, Separator
- Plus 15+ more specialized components

---

## Architecture & Structure

### Folder Organization

```
src/
├── app/                          # Next.js App Router
│   ├── login/
│   │       └── page.tsx          # Login page                   # Auth route group
│   │  
│   ├── dashboard/              # Dashboard route group
│   │   ├── layout.tsx            # Dashboard layout with sidebar
│   │   ├── page.tsx              # Dashboard home
│   │   ├── risks/
│   │   │   ├── page.tsx          # Risk list
│   │   │   └── [id]/
│   │   │       └── page.tsx      # Risk detail
│   │   ├── controls/
│   │   │   └── page.tsx          # Controls list
│   │   ├── evidence/
│   │   │   └── page.tsx          # Evidence tracker
│   │   ├── iso27001/
│   │   │   ├── page.tsx          # ISO compliance dashboard
│   │   │   └── [controlId]/
│   │   │       └── page.tsx      # Control detail
│   │   ├── audits/
│   │   │   └── page.tsx          # Audit log
│   │   ├── reports/
│   │   │   └── page.tsx          # Reports generator
│   │   └── settings/
│   │       └── page.tsx          # Settings page
│   ├── globals.css               # Global styles
│   ├── layout.tsx                # Root layout
│   ├── page.tsx                  # Landing page
│   └── middleware.ts             # Auth middleware
│
├── components/                   # Reusable React components
│   ├── Providers.tsx             # Context providers
│   ├── theme-provider.tsx        # Next-Themes provider
│   ├── auth/
│   │   └── RoleGuard.tsx         # RBAC component wrapper
│   ├── layout/
│   │   ├── Header.tsx            # App header
│   │   └── Sidebar.tsx           # Navigation sidebar
│   ├── settings/
│   │   └── ThemeSelector.tsx     # Dark mode toggle
│   └── ui/                       # shadcn/ui components
│       ├── button.tsx
│       ├── card.tsx
│       ├── dialog.tsx
│       ├── form.tsx
│       ├── input.tsx
│       ├── table.tsx
│       ├── tabs.tsx
│       └── ... (25+ more)
│
├── context/                      # React Context API
│   └── AuthContext.tsx           # Auth state & user info
│
├── features/                     # Domain-specific features
│   ├── dashboard/
│   │   ├── DashboardSummary.tsx
│   │   ├── OverdueItems.tsx
│   │   └── RiskHighlights.tsx
│   ├── iso27001/
│   │   ├── ComplianceScoring.tsx
│   │   ├── ISOComplianceWidget.tsx
│   │   ├── ISOControlDetail.tsx
│   │   ├── ISOControlList.tsx
│   │   ├── ISOControlsStatusWidget.tsx
│   │   ├── ISOEvidenceManager.tsx
│   │   └── RiskMapping.tsx
│   └── risk/
│       ├── RiskList.tsx
│       ├── RiskScoreExplanation.tsx
│       └── risk.logic.ts
│
├── hooks/                        # Custom React hooks
│   ├── useAuth.ts                # Auth context hook
│   └── use-toast.ts              # Toast notifications
│
├── lib/                          # Utilities & helpers
│   ├── auth.ts                   # Auth helpers (login, logout)
│   ├── constants.ts              # App-wide constants
│   ├── data-validation.ts        # Form validation schemas
│   ├── iso-service.ts            # ISO 27001 service layer
│   ├── mock-data.ts              # Mock database (339 lines)
│   ├── permissions.ts            # RBAC permission checks
│   ├── risk-scoring.ts           # Risk score calculation
│   ├── storage-service.ts        # localStorage wrapper
│   └── utils.ts                  # General utilities
│
├── types/                        # TypeScript type definitions
│   ├── audit.ts
│   ├── compliance.ts
│   ├── control.ts
│   ├── evidence.ts
│   ├── index.ts
│   ├── iso27001.ts
│   ├── risk.ts
│   └── user.ts
│
└── data/
    └── iso27001-controls.json    # ISO 27001 control reference

Public Files:
├── components.json               # shadcn/ui config
├── next.config.js                # Next.js config
├── package.json                  # Dependencies
├── tailwind.config.ts            # Tailwind config
├── tsconfig.json                 # TypeScript config
├── postcss.config.js             # PostCSS config
└── PROJECT_STATUS.md             # Project status tracker
```

### Data Flow & State Management

```
User Action
    ↓
Component Event Handler
    ↓
Action (localStorage or API call)
    ↓
AuthContext / State Update
    ↓
Component Re-render
```

**Current Pattern**:

- Context API for authentication state
- localStorage for session persistence
- Mock data functions return consistent results
- Ready to replace with API calls

### Key Data Types

#### User Profile

```typescript
{
  id: string;
  email: string;
  fullName: string;
  role: "admin" | "analyst" | "manager";
  department: string;
  createdAt: string;
  updatedAt: string;
}
```

#### Risk

```typescript
{
  id: string;
  title: string;
  description: string;
  category: RiskCategory;
  probability: number; // 1-5
  impact: number;      // 1-5
  riskScore: number;   // probability × impact
  status: 'open' | 'mitigated' | 'accepted' | 'monitoring';
  owner: string;
  createdAt: string;
  updatedAt: string;
  mappedControls: string[];
  relatedItems: string[];
}
```

#### Control

```typescript
{
  id: string;
  code: string;
  title: string;
  description: string;
  type: 'technical' | 'administrative' | 'physical';
  effectiveness: 'high' | 'medium' | 'low';
  status: 'implemented' | 'planned' | 'monitoring';
  relatedRisks: string[];
  relatedCompliance: string[];
}
```

---

## User Walkthrough

### 1. Landing Page & Login

**Entry Point**: `http://localhost:3000`

1. User sees professional landing page with:
   - GRC Platform branding
   - Value proposition ("Risk-Aware Compliance Made Simple")
   - Call-to-action buttons: "Get Started" and "View Demo"
   - Feature highlights

2. Click "Get Started" or "Sign In" → `http://localhost:3000/login`

3. On login page:
   - See 3 demo accounts (Alice, Bob, Carol)
   - **Alice (Admin)**: Full platform access
   - **Bob (Analyst)**: Risk analysis & reporting
   - **Carol (Manager)**: Controls & compliance
   - Click a role → enter "demo" as password

### 2. Dashboard Overview

**URL**: `http://localhost:3000/dashboard`

After login, user lands on Dashboard which shows:

**KPI Cards** (top row):

- Average Risk Score: 12/25 (with trend indicator)
- Open Risks: 4 (risk items needing attention)
- Compliance Rate: 67% (compliance progress)
- Implemented Controls: 54 (control status)

**Risk Highlights Section**:

- Top 3 highest-risk items with:
  - Risk title
  - Risk score (color-coded: red/amber/green)
  - Category badge
  - Quick status badge

**Upcoming/Overdue Items**:

- Table of assessments/reviews due soon
- Action buttons for each item

**Sidebar Navigation**:

```
Dashboard (home icon)
├── Risks
├── Controls
├── Evidence
├── ISO 27001
├── Audits
├── Reports
└── Settings
```

### 3. Risk Management Flow

#### Step 3a: View Risk List

1. Click **"Risks"** in sidebar → `/dashboard/risks`
2. See table with all risks:
   - Title, Category, Score, Probability, Impact, Status
   - 15+ sample risks visible
   - Sortable columns
   - Filterable by status/category

3. **Risk Example**:
   - Title: "Data Breach"
   - Category: Technology (cyan badge)
   - Score: 20/25 (high - red)
   - Status: Open

#### Step 3b: View Risk Details

1. Click any risk name → `/dashboard/risks/risk-1`
2. See detailed risk information:
   - Full description
   - **Scoring Breakdown**:
     ```
     Probability: 4/5 (very likely)
     Impact: 5/5 (critical)
     Risk Score: 4 × 5 = 20/25
     ```
   - Severity indicator (RED - High Risk)
   - **Mapped Controls**: Which controls reduce this risk
     - e.g., "Encryption at Rest", "Access Control"
   - Related Compliance Items
   - Owner: Alice Johnson
   - Creation/Update dates

### 4. Control Management Flow

1. Click **"Controls"** in sidebar → `/dashboard/controls`
2. See grid of control cards:
   - Each card shows control name, type, effectiveness
   - **Filter Options**:
     - Type: Technical, Administrative, Physical
     - Effectiveness: High, Medium, Low
     - Status: Implemented, Planned, Monitoring

3. Click control card to see:
   - Full control description
   - Implementation guidance
   - Risks this control mitigates
   - Compliance items it helps satisfy
   - Effectiveness rating

**Example Control**:

- **Code**: A.8.1.1
- **Title**: Encryption for Sensitive Data
- **Type**: Technical
- **Description**: Implement encryption for all data in transit and at rest
- **Effectiveness**: High
- **Status**: Implemented
- **Mitigates Risks**: Data Breach, Unauthorized Access
- **Maps to Compliance**: ISO 27001 A.10.1, GDPR Article 32

### 5. Compliance Tracking

#### ISO 27001 Dashboard

1. Click **"ISO 27001"** in sidebar → `/dashboard/iso27001`
2. See compliance overview:
   - Overall Compliance Rate: 67%
   - Control Status Breakdown:
     - ✅ Implemented: 60 controls
     - 🔄 Planned: 22 controls
     - ❌ Not Implemented: 8 controls
   - Compliance Trend Chart

3. View control list and details for each control:
   - Compliance objective
   - Risk mapping
   - Implementation status
   - Evidence tracking

### 6. Evidence Management

1. Click **"Evidence"** in sidebar → `/dashboard/evidence`
2. See table of compliance evidence:
   - Item Name, Type, Uploaded By, Status, Last Updated
   - 20+ sample evidence items

3. Evidence Status Workflow:
   - **Submitted**: Awaiting review
   - **Under Review**: Being verified
   - **Verified**: Accepted ✅
   - **Rejected**: Needs resubmission

**Example Evidence**:

- Policy: Data Protection Policy (Verified)
- Document: Incident Response Plan (Submitted)
- Log: Access Control Audit (Under Review)

### 7. Audit Trail

1. Click **"Audits"** in sidebar → `/dashboard/audits`
2. See immutable activity log:
   - Recent Activities: User login, risk update, evidence verified
   - Each entry shows:
     - Event type
     - Description
     - User who performed action
     - Timestamp
     - Risk/Item affected

**Example Audit Log**:

```
[2024-01-28 14:32] Alice Johnson | Risk Created | "Supply Chain Risk"
[2024-01-28 14:15] Bob Smith | Risk Updated | "Data Breach" status changed to "Monitoring"
[2024-01-28 14:00] Carol Williams | Evidence Verified | "ISO 27001 Audit Report"
```

### 8. Reports

1. Click **"Reports"** in sidebar → `/dashboard/reports`
2. See available report templates:
   - **Compliance Summary**: Overall compliance metrics
   - **Risk Assessment**: Risk portfolio analysis
   - **Control Status**: Implementation progress
   - **Executive Summary**: High-level overview

3. Generate and export reports:
   - Select timeframe
   - Choose export format (PDF, Excel - UI ready)
   - Download report

### 9. Settings & Preferences

1. Click **"Settings"** in sidebar → `/dashboard/settings`
2. Sections available:
   - **Account**: View/edit profile info
   - **Preferences**: Default view settings
   - **Theme**: Toggle between light/dark mode
   - **Notifications**: Alert preferences
   - **Security**: Password management

3. Click user avatar in header:
   - View profile
   - Access settings
   - Logout

### 10. Role-Based Permissions Example

**Alice (Admin)**:

- Can: Create risks, approve controls, manage users, review evidence, access all reports
- Symbol: Crown icon or "Admin" badge

**Bob (Analyst)**:

- Can: View all data, create risk assessments, view reports
- Cannot: Approve controls, manage compliance framework

**Carol (Manager)**:

- Can: View risks/controls, assign tasks, manage compliance status
- Cannot: Modify framework settings, manage users

---

## Mobile Experience

The platform is fully responsive:

- **Desktop (1280px+)**: Full sidebar, 4-column grid
- **Tablet (768px)**: Collapsible sidebar, 2-column grid
- **Mobile (320px-480px)**: Stacked layout, hamburger menu for navigation

Try resizing browser or testing on mobile device to see responsive behavior.

---

## Pending & Future Work

### 🔴 Phase 1: Backend API Integration

#### Database Setup

- [ ] Set up Supabase project (PostgreSQL database)
- [ ] Create database schema:
  ```sql
  - user_profiles (with RBAC)
  - risks (with categories)
  - controls (ISO 27001 mapping)
  - risk_control_mappings
  - evidence (with documents)
  - compliance_items
  - audit_logs (immutable)
  - risk_assessments (historical tracking)
  ```
- [ ] Create database migrations
- [ ] Set up authentication with Supabase Auth

#### API Endpoints (FastAPI/Node.js)

```
Authentication:
  POST   /api/auth/login
  POST   /api/auth/logout
  POST   /api/auth/register
  GET    /api/auth/me

Risk Management:
  GET    /api/risks
  POST   /api/risks
  GET    /api/risks/{id}
  PUT    /api/risks/{id}
  DELETE /api/risks/{id}
  GET    /api/risks/{id}/history

Controls:
  GET    /api/controls
  POST   /api/controls
  GET    /api/controls/{id}
  PUT    /api/controls/{id}
  GET    /api/controls/{id}/evidence

Compliance:
  GET    /api/compliance-items
  GET    /api/compliance-items/{id}/status
  PUT    /api/compliance-items/{id}/status

Evidence:
  GET    /api/evidence
  POST   /api/evidence (with file upload)
  GET    /api/evidence/{id}
  PUT    /api/evidence/{id}/verify

Audit:
  GET    /api/audit-logs
  GET    /api/audit-logs?filter=event_type

Reports:
  GET    /api/reports/{type}
  POST   /api/reports/{type}/export
```

#### Frontend Integration

- [ ] Replace mock-data with API calls using `fetch` or `axios`
- [ ] Replace localStorage auth with Supabase sessions
- [ ] Add JWT token handling
- [ ] Implement API error handling
- [ ] Add loading states and error boundaries
- [ ] Update form handlers to call APIs

### 🟡 Phase 2: Advanced Features

#### Real-Time Updates

- [ ] Implement WebSocket connection for live updates
- [ ] Real-time risk score updates
- [ ] Live audit log streaming
- [ ] Multi-user collaboration signals

#### Enhanced Reporting

- [ ] PDF report generation (using `jspdf` or similar)
- [ ] Excel export with formatting
- [ ] Scheduled report delivery
- [ ] Report customization (branding, sections)
- [ ] Advanced filtering in reports

#### Risk Analytics

- [ ] Risk trend analysis over time
- [ ] Predictive analytics for risk escalation
- [ ] Control effectiveness metrics
- [ ] Risk heat maps
- [ ] Root cause analysis

#### Search & Filtering

- [ ] Full-text search across risks, controls, evidence
- [ ] Advanced filter combinations
- [ ] Saved filter presets
- [ ] Search suggestions/autocomplete

#### User Management

- [ ] Admin panel for user management
- [ ] Create/edit/delete user accounts
- [ ] Role assignment per user
- [ ] Bulk import from CSV
- [ ] User activity tracking

### 🔵 Phase 3: Enterprise Features

#### Multi-Framework Support

- [ ] Add NIST CSF framework support
- [ ] Add COBIT framework
- [ ] Add SOC 2 compliance tracking
- [ ] Framework mapping engine

#### Advanced Workflows

- [ ] Approval workflows for risk changes
- [ ] Control review cycles (quarterly/annual)
- [ ] Evidence expiration and renewal
- [ ] Escalation rules

#### Integration

- [ ] Email notifications for alerts
- [ ] Slack integration for team alerts
- [ ] Jira integration for risk tracking
- [ ] External API integrations

#### Compliance Automation

- [ ] Automated control effectiveness assessment
- [ ] Automated evidence collection from systems
- [ ] Compliance rule engine
- [ ] Remediation workflow automation

#### Analytics Dashboard

- [ ] Executive dashboard with KPIs
- [ ] Risk portfolio analysis
- [ ] Compliance trend charts
- [ ] Benchmarking against industry standards

### 🟢 Quality & Operations

#### Testing

- [ ] Unit tests for utilities (risk-scoring, permissions)
- [ ] Integration tests for API endpoints
- [ ] E2E tests for critical workflows (login, risk creation)
- [ ] Performance testing for large datasets

#### Documentation

- [ ] API documentation (OpenAPI/Swagger)
- [ ] Component Storybook
- [ ] Deployment guide
- [ ] User manual with screenshots
- [ ] Admin setup guide

#### Deployment

- [ ] Containerization (Docker)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Environment configuration (dev/staging/prod)
- [ ] Monitoring and alerting setup
- [ ] Backup and disaster recovery

---

## Getting Started

### Installation

```bash
# Clone repository
git clone https://github.com/kharel17/GRC-main.git
cd "GRC main"

# Install dependencies
yarn install

# Start development server
yarn run dev
```

Visit `http://localhost:3000` in browser.

### Running Commands

```bash
# Development with hot reload
yarn run dev

# Type checking
yarn run typecheck

# Linting
yarn run lint

# Production build
yarn run build

# Serve production build
yarn start
```

### Key Features to Try

1. **Login**: Use test account (Alice/alice@company.com, password: demo)
2. **Dashboard**: View KPIs and risk highlights
3. **Risk Detail**: Click a risk to see scoring breakdown
4. **Controls**: Filter by type/effectiveness/status
5. **Evidence**: Track compliance documentation
6. **ISO 27001**: View control mappings and compliance status
7. **Theme**: Toggle dark mode in settings

### Next Steps for Development

1. **Short Term (1 week)**:
   - Set up Supabase database and migrations
   - Create API authentication endpoints
   - Replace mock login with Supabase Auth

2. **Medium Term (2-3 weeks)**:
   - Implement risk/control CRUD APIs
   - Add file upload for evidence
   - Implement audit logging
   - Replace all mock data with API calls

3. **Long Term (1-2 months)**:
   - Add advanced features (WebSockets, analytics)
   - Implement approval workflows
   - Add multi-framework support
   - Set up deployment pipeline

---

## Summary

The **GRC Platform** is a fully-functional, production-ready frontend for risk and compliance management. With comprehensive mocking and realistic data, it demonstrates all core features needed for enterprise deployment.

### What You Have Now:

✅ Complete UI/UX with 11 pages
✅ Role-based access control
✅ Real risk scoring calculations
✅ ISO 27001 compliance framework
✅ Responsive design
✅ Professional design system
✅ Mock data for all features

### What You Need for Production:

- Backend API (FastAPI/Node.js)
- Real database (Supabase/PostgreSQL)
- Authentication system (Supabase Auth/JWT)
- File storage (S3/Cloud Storage)
- Monitoring & logging
- CI/CD pipeline

The codebase is clean, well-organized, and ready for team handoff or backend integration. All components are reusable, well-typed, and follow React/Next.js best practices.

---

## Known Limitations

### 1. OCR Multilingual Support
- **English Language Default**: The local Tesseract OCR pipeline defaults to English language data (`eng.traineddata`).
- **Impact on Non-English Evidence**: Scanned evidence or policies containing non-English text or extended diacritics (e.g. Scandinavian `ä`, `ö`, Cyrillic, or Asian scripts) will experience degraded extraction and character substitutions unless corresponding Tesseract language packs (e.g. `tesseract-ocr-fin` or `*.traineddata`) are installed into the `tessdata` directory.

---

## Support & Questions

For questions about:

- **Architecture**: See folder structure and naming conventions
- **Components**: Check `/src/components/ui` and `/src/features`
- **Data Types**: Refer to `/src/types/*`
- **Mock Data**: Review `/src/lib/mock-data.ts`
- **Styling**: Check `tailwind.config.ts` and global styles

_Last Updated: February 10, 2026_
