import asyncio
from app.database import engine, SessionLocal
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.risk import Risk, RiskCategory, RiskStatus
from app.models.control import Control, ControlType, ControlEffectiveness, ControlStatus
from app.models.compliance import ComplianceItem, ComplianceStatus, CompliancePriority
from app.models.evidence import Evidence, EvidenceRelatedTo
from app.models.audit_log import AuditLog, AuditAction, AuditEntityType
from app.models.ticket import Ticket, TicketPriority, TicketStatus, TicketCategory, TicketComment
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
        # Users
        users = [
            User(id=uuid.UUID('00000000-0000-0000-0000-000000000001'), email="alice@company.com", full_name="Alice Johnson", hashed_password=hash_password("demo"), role=UserRole.admin, department="Compliance"),
            User(id=uuid.UUID('00000000-0000-0000-0000-000000000002'), email="bob@company.com", full_name="Bob Smith", hashed_password=hash_password("demo"), role=UserRole.analyst, department="Risk Management"),
            User(id=uuid.UUID('00000000-0000-0000-0000-000000000003'), email="carol@company.com", full_name="Carol Williams", hashed_password=hash_password("demo"), role=UserRole.manager, department="Operations"),
        ]
        session.add_all(users)
        await session.flush()

        # Risk Categories
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

        # Risks
        risks = [
            Risk(title="Data Breach", description="Unauthorized access to sensitive customer data", category_id=categories[5].id, likelihood=3, impact=5, risk_score=15, status=RiskStatus.assessed, owner_id=users[1].id, created_by=users[1].id),
            Risk(title="Regulatory Non-Compliance", description="Failure to meet GDPR requirements", category_id=categories[2].id, likelihood=2, impact=4, risk_score=8, status=RiskStatus.identified, owner_id=users[1].id, created_by=users[0].id),
            Risk(title="System Downtime", description="Critical infrastructure failure", category_id=categories[0].id, likelihood=2, impact=4, risk_score=8, status=RiskStatus.mitigated, owner_id=users[1].id, created_by=users[1].id),
            Risk(title="Budget Overrun", description="Project expenses exceed allocated budget", category_id=categories[1].id, likelihood=3, impact=3, risk_score=9, status=RiskStatus.identified, owner_id=users[1].id, created_by=users[0].id),
            Risk(title="Key Person Dependency", description="Critical functions dependent on single individual", category_id=categories[3].id, likelihood=4, impact=3, risk_score=12, status=RiskStatus.assessed, owner_id=users[1].id, created_by=users[1].id),
        ]
        session.add_all(risks)
        await session.flush()

        # Controls
        controls = [
            Control(title="Access Control Policy", description="Implement robust access controls for all system access", control_type=ControlType.preventive, effectiveness=ControlEffectiveness.high, status=ControlStatus.implemented, owner_id=users[1].id, created_by=users[1].id),
            Control(title="Security Awareness Training", description="Quarterly training for all employees", control_type=ControlType.preventive, effectiveness=ControlEffectiveness.medium, status=ControlStatus.implemented, owner_id=users[1].id, created_by=users[0].id),
            Control(title="Data Encryption", description="Encrypt all data at rest and in transit", control_type=ControlType.preventive, effectiveness=ControlEffectiveness.high, status=ControlStatus.implemented, owner_id=users[1].id, created_by=users[1].id),
            Control(title="Audit Logging", description="Comprehensive audit trail for all system actions", control_type=ControlType.detective, effectiveness=ControlEffectiveness.high, status=ControlStatus.under_review, owner_id=users[1].id, created_by=users[1].id),
            Control(title="Disaster Recovery Plan", description="Documented and tested disaster recovery procedures", control_type=ControlType.corrective, effectiveness=ControlEffectiveness.medium, status=ControlStatus.planned, owner_id=users[1].id, created_by=users[0].id),
        ]
        session.add_all(controls)
        await session.flush()

        # Compliance Items
        compliance = [
            ComplianceItem(framework="GDPR", requirement_id="GDPR-5.1", title="Data Protection Officer", description="Designate DPO", status=ComplianceStatus.compliant, priority=CompliancePriority.critical, owner_id=users[0].id, due_date=datetime.now() + timedelta(days=5)),
            ComplianceItem(framework="SOC2", requirement_id="CC6.1", title="Logical Access Controls", description="Access control mechanisms", status=ComplianceStatus.in_progress, priority=CompliancePriority.high, owner_id=users[1].id, due_date=datetime.now() + timedelta(days=15)),
            ComplianceItem(framework="ISO27001", requirement_id="A.12.4.1", title="Event Logging", description="Recording user activities", status=ComplianceStatus.not_started, priority=CompliancePriority.medium, owner_id=users[1].id, due_date=datetime.now() + timedelta(days=45)),
        ]
        session.add_all(compliance)
        await session.flush()

        # Evidence
        evidence = [
            Evidence(title="Access Control Implementation Report", description="Verification of access control", file_url="/documents/access-control-report.pdf", file_name="access-control-report.pdf", file_type="pdf", file_size=2048000, related_to=EvidenceRelatedTo.control, related_id=controls[0].id, uploaded_by=users[1].id, verified=True, verified_by=users[0].id, verified_at=datetime.utcnow()),
            Evidence(title="GDPR DPO Notification", description="Official notification", file_url="/documents/dpo-notification.pdf", file_name="dpo-notification.pdf", file_type="pdf", file_size=512000, related_to=EvidenceRelatedTo.compliance_item, related_id=compliance[0].id, uploaded_by=users[0].id, verified=True, verified_by=users[0].id, verified_at=datetime.utcnow()),
        ]
        session.add_all(evidence)
        await session.flush()

        # Audit Logs
        audit_logs = [
            AuditLog(id=uuid.UUID('00000000-0000-0000-0000-000000000101'), user_id=users[1].id, action=AuditAction.created, entity_type=AuditEntityType.risk, entity_id=risks[0].id, entity_name=risks[0].title, description="New risk identified", timestamp=datetime.utcnow() - timedelta(days=10)),
            AuditLog(id=uuid.UUID('00000000-0000-0000-0000-000000000102'), user_id=users[0].id, action=AuditAction.updated, entity_type=AuditEntityType.risk, entity_id=risks[0].id, entity_name=risks[0].title, old_values={"status": "identified"}, new_values={"status": "assessed"}, description="Risk status updated", timestamp=datetime.utcnow() - timedelta(days=9)),
            AuditLog(id=uuid.UUID('00000000-0000-0000-0000-000000000103'), user_id=users[1].id, action=AuditAction.created, entity_type=AuditEntityType.evidence, entity_id=evidence[0].id, entity_name=evidence[0].title, description="Evidence uploaded", timestamp=datetime.utcnow() - timedelta(days=8)),
        ]
        session.add_all(audit_logs)
        await session.flush()

        # Tickets
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
                escalated_to_id=None, # Simplified
                escalated_to_role="CTO",
                escalation_level=3,
                related_risk_id=risks[0].id,
                related_entity_type="risk",
                related_entity_id=risks[0].id,
                created_by=users[1].id,
                created_at=datetime.utcnow() - timedelta(days=5),
                escalated_at=datetime.utcnow() - timedelta(days=4)
            ),
             Ticket(
                id=uuid.UUID('00000000-0000-0000-0000-000000000202'),
                title="Regulatory Non-Compliance Gap - GDPR Requirements",
                description="GDPR compliance gap identified.",
                priority=TicketPriority.high,
                status=TicketStatus.in_progress,
                category=TicketCategory.compliance_gap,
                source_audit_log_id=audit_logs[1].id,
                assigned_to_id=users[0].id,
                assigned_to_role="Compliance Manager",
                escalation_level=2,
                related_risk_id=risks[1].id,
                related_entity_type="risk",
                related_entity_id=risks[1].id,
                created_by=users[0].id,
                created_at=datetime.utcnow() - timedelta(days=3),
            )
        ]
        session.add_all(tickets)
        await session.flush()
        
        # Comments
        comments = [
            TicketComment(ticket_id=tickets[0].id, author_id=users[1].id, text="Escalating for review due to risk score."),
            TicketComment(ticket_id=tickets[0].id, author_id=users[0].id, text="Reviewed, approved escalation."),
        ]
        session.add_all(comments)
        
        await session.commit()
    
    print("Database seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_data())
