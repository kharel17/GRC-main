import asyncio
import sys
import os
import json
import uuid
from pathlib import Path
import bcrypt

# Add the current directory to sys.path to resolve 'app' imports correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.organization import Organization, OrganizationSize
from app.models.framework import Framework
from app.models.framework_control import FrameworkControl
from app.models.control_applicability import ControlApplicability, ControlImplementationStatus

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
        # ── Real Organization ─────────────────────────────
        REAL_ORG_ID = uuid.UUID('24de3639-ee40-4563-a207-dd66436a0da8')
        org = Organization(
            id=REAL_ORG_ID,
            name="My Organization",
            industry="Technology",
            size=OrganizationSize.medium,
            description="Active tenant organization.",
            onboarding_completed=True
        )
        session.add(org)
        await session.flush()

        # ── Active Developer/Admin Users ──────────────────
        hashed_password = hash_password("demo")
        users = [
            User(
                email="bcolorc17@gmail.com",
                full_name="Admin User",
                hashed_password=hashed_password,
                role=UserRole.admin,
                is_active=True,
                invitation_status="active",
                organization_id=org.id,
                organization_name=org.name
            ),
            User(
                email="grchelios@gmail.com",
                full_name="Developer User",
                hashed_password=hashed_password,
                role=UserRole.admin,
                is_active=True,
                invitation_status="active",
                organization_id=org.id,
                organization_name=org.name
            ),
        ]
        session.add_all(users)
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
                category=None
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
        # Seed control applicability with defaults (all applicable, status not_started)
        control_applicabilities = []
        for ctrl in iso_data.get("controls", []):
            annex = ctrl["id"]
            fc = control_map.get(annex)
            
            ca = ControlApplicability(
                organization_id=org.id,
                control_annex=annex,
                framework_control_id=getattr(fc, 'id', None),
                is_applicable=True,
                status=ControlImplementationStatus.not_started,
                responsible_id=users[0].id
            )
            control_applicabilities.append(ca)
        
        session.add_all(control_applicabilities)
        await session.flush()
        
        await session.commit()
    
    # Print summary
    print("=" * 60)
    print("Database seeded with production readiness template successfully!")
    print("=" * 60)
    print("  Users:                  2 (Real users)")
    print(f"  Organization:           1 (Real organization: {org.name})")
    print("  Frameworks:             1 (ISO 27001)")
    print(f"  Framework Controls:     {len(framework_controls)}")
    print(f"  Control Applicability:  {len(control_applicabilities)} (all ISO 27001 controls for real org)")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(seed_data())
