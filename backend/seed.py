import asyncio
import sys
import os
import json
from pathlib import Path

# Add the current directory to sys.path to resolve 'app' imports correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.organization import Organization, OrganizationSize
from app.models.asset import Asset, AssetType, AssetClassification, AssetCriticality, CIAValue
from app.models.risk import Risk, RiskCategory, RiskStatus
from app.models.control import Control, ControlType, ControlEffectiveness, ControlStatus, RiskControlMapping
from app.models.compliance import ComplianceItem, ComplianceStatus, CompliancePriority
from app.models.evidence import Evidence, EvidenceRelatedTo
from app.models.audit_log import AuditLog, AuditAction, AuditEntityType
from app.models.ticket import Ticket, TicketPriority, TicketStatus, TicketCategory, TicketComment
from app.models.framework import Framework
from app.models.framework_control import FrameworkControl
from app.models.control_applicability import ControlApplicability, ControlImplementationStatus
from app.models.notification import Notification
import uuid
from datetime import datetime, timedelta
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Create tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def seed_data():
    await init_db()
    
    async with SessionLocal() as session:
        # ── Users ────────────────────────────────────────
        users = [
            User(id=uuid.UUID('00000000-0000-0000-0000-000000000001'), email="alice@company.com", full_name="Alice Johnson", hashed_password=hash_password("demo"), role=UserRole.admin, department="Compliance"),
            User(id=uuid.UUID('00000000-0000-0000-0000-000000000002'), email="bob@company.com", full_name="Bob Smith", hashed_password=hash_password("demo"), role=UserRole.analyst, department="Risk Management"),
            User(id=uuid.UUID('00000000-0000-0000-0000-000000000003'), email="carol@company.com", full_name="Carol Williams", hashed_password=hash_password("demo"), role=UserRole.manager, department="Operations"),
        ]
        session.add_all(users)
        await session.flush()

        # ── Organization ─────────────────────────────────
        org = Organization(
            id=uuid.UUID('00000000-0000-0000-0000-000000000010'),
            name="Acme Corporation",
            industry="Technology",
            size=OrganizationSize.medium,
            description="A mid-sized technology company specializing in cloud services and SaaS products.",
            website="https://acme-corp.example.com",
            country="United States",
            compliance_frameworks=["ISO 27001", "SOC2", "GDPR"],
            primary_contact_id=users[0].id,
        )
        session.add(org)
        await session.flush()

        # ── Assets ───────────────────────────────────────
        assets = [
            Asset(name="Customer Database", description="Primary PostgreSQL database containing customer PII and account data", type=AssetType.data, classification=AssetClassification.restricted, criticality=AssetCriticality.critical, location="AWS us-east-1", owner_id=users[0].id, organization_id=org.id, confidentiality=CIAValue.high, integrity=CIAValue.high, availability=CIAValue.high),
            Asset(name="Source Code Repository", description="GitHub Enterprise repositories for all product codebases", type=AssetType.software, classification=AssetClassification.confidential, criticality=AssetCriticality.high, location="GitHub Cloud", owner_id=users[1].id, organization_id=org.id, confidentiality=CIAValue.high, integrity=CIAValue.high, availability=CIAValue.medium),
            Asset(name="Internal Wiki", description="Confluence-based internal documentation and knowledge base", type=AssetType.software, classification=AssetClassification.internal, criticality=AssetCriticality.medium, location="Atlassian Cloud", owner_id=users[2].id, organization_id=org.id, confidentiality=CIAValue.medium, integrity=CIAValue.medium, availability=CIAValue.medium),
            Asset(name="Payment Processing Service", description="Stripe integration service handling financial transactions", type=AssetType.service, classification=AssetClassification.restricted, criticality=AssetCriticality.critical, location="AWS us-east-1", owner_id=users[0].id, organization_id=org.id, confidentiality=CIAValue.high, integrity=CIAValue.high, availability=CIAValue.high),
            Asset(name="Employee Laptops", description="Company-issued MacBook Pro and Dell laptops", type=AssetType.hardware, classification=AssetClassification.confidential, criticality=AssetCriticality.high, location="Global offices and remote", owner_id=users[2].id, organization_id=org.id, confidentiality=CIAValue.medium, integrity=CIAValue.high, availability=CIAValue.medium),
        ]
        session.add_all(assets)
        await session.flush()

        # ── Risk Categories ──────────────────────────────
        categories = [
            RiskCategory(name="Operational", description="Day-to-day operational risks", color="#3b82f6"),
            RiskCategory(name="Financial", description="Financial stability risks", color="#10b981"),
            RiskCategory(name="Compliance", description="Regulatory compliance risks", color="#f59e0b"),
            RiskCategory(name="Strategic", description="Long-term strategy risks", color="#8b5cf6"),
            RiskCategory(name="Reputational", description="Brand and reputation risks", color="#ef4444"),
            RiskCategory(name="Technology", description="IT and cybersecurity risks", color="#06b6d4"),
        ]
        session.add_all(categories)
        await session.flush()

        # ── Risks (now with organization_id) ─────────────
        risks = [
            Risk(title="Data Breach", description="Unauthorized access to sensitive customer data", category_id=categories[5].id, asset_id=assets[0].id, threat="Cyber Attack / SQL Injection", vulnerability="Unpatched software vulnerabilities", likelihood=3, impact=5, risk_score=15, status=RiskStatus.assessed, owner_id=users[1].id, created_by=users[1].id, organization_id=org.id),
            Risk(title="Regulatory Non-Compliance", description="Failure to meet GDPR requirements", category_id=categories[2].id, asset_id=assets[0].id, threat="Oversight / Legal change", vulnerability="Lack of formal DPO role", likelihood=2, impact=4, risk_score=8, status=RiskStatus.identified, owner_id=users[1].id, created_by=users[0].id, organization_id=org.id),
            Risk(title="Source Code Leak", description="Proprietary code exposed publicly", category_id=categories[5].id, asset_id=assets[1].id, threat="Insider threat / Accidental push", vulnerability="Misconfigured repository permissions", likelihood=2, impact=4, risk_score=8, status=RiskStatus.mitigated, owner_id=users[1].id, created_by=users[1].id, organization_id=org.id),
            Risk(title="Service Outage", description="Payment Gateway becomes unavailable", category_id=categories[0].id, asset_id=assets[3].id, threat="Cloud provider failure", vulnerability="Single region deployment", likelihood=3, impact=4, risk_score=12, status=RiskStatus.assessed, owner_id=users[1].id, created_by=users[1].id, organization_id=org.id),
        ]
        session.add_all(risks)
        await session.flush()

        # ── Controls ─────────────────────────────────────
        controls = [
            Control(title="Access Control Policy", description="Implement robust access controls for all system access", control_type=ControlType.preventive, effectiveness=ControlEffectiveness.high, status=ControlStatus.implemented, owner_id=users[1].id, created_by=users[1].id),
            Control(title="Security Awareness Training", description="Quarterly training for all employees", control_type=ControlType.preventive, effectiveness=ControlEffectiveness.medium, status=ControlStatus.implemented, owner_id=users[1].id, created_by=users[0].id),
            Control(title="Data Encryption", description="Encrypt all data at rest and in transit", control_type=ControlType.preventive, effectiveness=ControlEffectiveness.high, status=ControlStatus.implemented, owner_id=users[1].id, created_by=users[1].id),
            Control(title="Audit Logging", description="Comprehensive audit trail for all system actions", control_type=ControlType.detective, effectiveness=ControlEffectiveness.high, status=ControlStatus.under_review, owner_id=users[1].id, created_by=users[1].id),
            Control(title="Disaster Recovery Plan", description="Documented and tested disaster recovery procedures", control_type=ControlType.corrective, effectiveness=ControlEffectiveness.medium, status=ControlStatus.planned, owner_id=users[1].id, created_by=users[0].id),
        ]
        session.add_all(controls)
        await session.flush()


        # ── Compliance Items (now with organization_id) ──
        compliance = [
            ComplianceItem(framework="GDPR", requirement_id="GDPR-5.1", title="Data Protection Officer", description="Designate DPO", status=ComplianceStatus.compliant, priority=CompliancePriority.critical, owner_id=users[0].id, organization_id=org.id, due_date=datetime.now() + timedelta(days=5)),
            ComplianceItem(framework="SOC2", requirement_id="CC6.1", title="Logical Access Controls", description="Access control mechanisms", status=ComplianceStatus.in_progress, priority=CompliancePriority.high, owner_id=users[1].id, organization_id=org.id, due_date=datetime.now() + timedelta(days=15)),
            ComplianceItem(framework="ISO27001", requirement_id="A.12.4.1", title="Event Logging", description="Recording user activities", status=ComplianceStatus.not_started, priority=CompliancePriority.medium, owner_id=users[1].id, organization_id=org.id, due_date=datetime.now() + timedelta(days=45)),
        ]
        session.add_all(compliance)
        await session.flush()

        # ── Evidence (now with organization_id) ──────────
        evidence = [
            Evidence(title="Access Control Implementation Report", description="Verification of access control", file_url="/documents/access-control-report.pdf", file_name="access-control-report.pdf", file_type="pdf", file_size=2048000, related_to=EvidenceRelatedTo.control, related_id=controls[0].id, uploaded_by=users[1].id, organization_id=org.id, verified=True, verified_by=users[0].id, verified_at=datetime.utcnow()),
            Evidence(title="GDPR DPO Notification", description="Official notification", file_url="/documents/dpo-notification.pdf", file_name="dpo-notification.pdf", file_type="pdf", file_size=512000, related_to=EvidenceRelatedTo.compliance_item, related_id=compliance[0].id, uploaded_by=users[0].id, organization_id=org.id, verified=True, verified_by=users[0].id, verified_at=datetime.utcnow()),
        ]
        session.add_all(evidence)
        await session.flush()

        # ── Frameworks ───────────────────────────────────
        iso_framework = Framework(
            id=uuid.UUID('00000000-0000-0000-0000-000000001000'),
            name="ISO 27001",
            version="2022",
            description="Information security management systems — Requirements",
        )
        session.add(iso_framework)
        await session.flush()

        # ── Framework Controls (Library) ──────────────────
        controls_json_path = Path(__file__).parent / "data" / "iso27001-controls.json"
        with open(controls_json_path, "r", encoding="utf-8") as f:
            iso_data = json.load(f)
        
        framework_controls = []
        control_map = {} # map code/annex to ID
        for ctrl_data in iso_data.get("controls", []):
            fc = FrameworkControl(
                framework_id=iso_framework.id,
                code=ctrl_data["annex"],
                title=ctrl_data["title"],
                description=ctrl_data["description"],
                category=None # Could map from clauseId if needed
            )
            framework_controls.append(fc)
            control_map[ctrl_data["annex"]] = fc

        session.add_all(framework_controls)
        await session.flush()

        # ── Organization Linkage ─────────────────────────
        org.framework_id = iso_framework.id
        org.isms_scope = "All internal cloud services, SaaS products, and supporting corporate infrastructure."
        session.add(org)

        # ── Control Applicability (SoA) ──────────────────
        # Sample: mark some controls as implemented, some in-progress, most as not_started
        implemented_controls = {"5.1", "5.2", "5.15", "5.17", "6.3", "8.5", "8.24"}
        in_progress_controls = {"5.9", "5.12", "5.34", "8.7", "8.13", "8.15"}
        not_applicable_controls = {"7.1", "7.2", "7.3", "7.4", "7.5", "7.6"}  # physical security N/A for cloud-first company
        
        control_applicabilities = []
        for ctrl in iso_data.get("controls", []):
            annex = ctrl["id"]
            fc = control_map.get(annex)
            
            if annex in implemented_controls:
                status = ControlImplementationStatus.implemented
            elif annex in in_progress_controls:
                status = ControlImplementationStatus.in_progress
            elif annex in not_applicable_controls:
                status = ControlImplementationStatus.not_applicable
            else:
                status = ControlImplementationStatus.not_started
            
            ca = ControlApplicability(
                organization_id=org.id,
                control_annex=annex,
                framework_control_id=getattr(fc, 'id', None),
                is_applicable=(annex not in not_applicable_controls),
                status=status,
                justification="Physical security controls not applicable — fully cloud-hosted infrastructure" if annex in not_applicable_controls else None,
                responsible_id=users[0].id if status == ControlImplementationStatus.implemented else (users[1].id if status != ControlImplementationStatus.not_applicable else None),
            )
            control_applicabilities.append(ca)
        
        session.add_all(control_applicabilities)
        await session.flush()

        # ── Risk-Control Mapping ─────────────────────────
        # Map Data Breach risk to Access Control Policy (A.9.2.1/A.9.4.2 in 2013, 5.15 in 2022)
        # Note: using the ISO 2022 framework control
        fc_access = control_map.get("5.15")
        mapping = RiskControlMapping(
            risk_id=risks[0].id,
            framework_control_id=getattr(fc_access, 'id', None),
            residual_likelihood=2,
            residual_impact=4,
            residual_risk_score=8,
            mapped_by=users[0].id
        )
        session.add(mapping)
        await session.flush()

        # ── Audit Logs ───────────────────────────────────
        audit_logs = [
            AuditLog(id=uuid.UUID('00000000-0000-0000-0000-000000000101'), user_id=users[1].id, action=AuditAction.created, entity_type=AuditEntityType.risk, entity_id=risks[0].id, entity_name=risks[0].title, description="New risk identified", timestamp=datetime.utcnow() - timedelta(days=10)),
            AuditLog(id=uuid.UUID('00000000-0000-0000-0000-000000000102'), user_id=users[0].id, action=AuditAction.updated, entity_type=AuditEntityType.risk, entity_id=risks[0].id, entity_name=risks[0].title, old_values={"status": "identified"}, new_values={"status": "assessed"}, description="Risk status updated", timestamp=datetime.utcnow() - timedelta(days=9)),
            AuditLog(id=uuid.UUID('00000000-0000-0000-0000-000000000103'), user_id=users[1].id, action=AuditAction.created, entity_type=AuditEntityType.evidence, entity_id=evidence[0].id, entity_name=evidence[0].title, description="Evidence uploaded", timestamp=datetime.utcnow() - timedelta(days=8)),
        ]
        session.add_all(audit_logs)
        await session.flush()

        # ── Tickets (now with organization_id) ───────────
        tickets = [
            Ticket(
                id=uuid.UUID('00000000-0000-0000-0000-000000000201'),
                title="Critical: Data Breach Risk Requires Executive Review",
                description="A high-severity data breach risk (score 15) has been identified.",
                priority=TicketPriority.critical,
                status=TicketStatus.escalated,
                category=TicketCategory.risk_identified,
                source_audit_log_id=audit_logs[0].id,
                assigned_to_id=users[0].id,
                assigned_to_role="ISO Officer",
                escalated_to_id=None,
                escalated_to_role="CTO",
                escalation_level=3,
                related_risk_id=risks[0].id,
                related_entity_type="risk",
                related_entity_id=risks[0].id,
                organization_id=org.id,
                created_by=users[1].id,
                created_at=datetime.utcnow() - timedelta(days=5),
                escalated_at=datetime.utcnow() - timedelta(days=4)
            ),
             Ticket(
                id=uuid.UUID('00000000-0000-0000-0000-000000000202'),
                title="Regulatory Non-Compliance Gap - GDPR Requirements",
                description="GDPR compliance gap identified.",
                priority=TicketPriority.high,
                status=TicketStatus.in_review,
                category=TicketCategory.compliance_gap,
                source_audit_log_id=audit_logs[1].id,
                assigned_to_id=users[0].id,
                assigned_to_role="Compliance Manager",
                escalation_level=2,
                related_risk_id=risks[1].id,
                related_entity_type="risk",
                related_entity_id=risks[1].id,
                organization_id=org.id,
                created_by=users[0].id,
                created_at=datetime.utcnow() - timedelta(days=3),
            )
        ]
        session.add_all(tickets)
        await session.flush()
        
        # ── Comments ─────────────────────────────────────
        comments = [
            TicketComment(ticket_id=tickets[0].id, author_id=users[1].id, text="Escalating for review due to risk score."),
            TicketComment(ticket_id=tickets[0].id, author_id=users[0].id, text="Reviewed, approved escalation."),
        ]
        session.add_all(comments)
        
        await session.commit()
    
    # Print summary
    print("=" * 60)
    print("Database seeded successfully!")
    print("=" * 60)
    print(f"  Users:                  3")
    print(f"  Organization:           1 (Acme Corporation)")
    print(f"  Assets:                 {len(assets)}")
    print(f"  Risk Categories:        {len(categories)}")
    print(f"  Risks:                  {len(risks)}")
    print(f"  Controls:               {len(controls)}")
    print(f"  Compliance Items:       {len(compliance)}")
    print(f"  Evidence:               {len(evidence)}")
    print(f"  Frameworks:             1 (ISO 27001)")
    print(f"  Framework Controls:     {len(framework_controls)}")
    print(f"  Control Applicability:  {len(control_applicabilities)} (all ISO 27001 controls)")
    print(f"  Audit Logs:             {len(audit_logs)}")
    print(f"  Tickets:                {len(tickets)}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(seed_data())
