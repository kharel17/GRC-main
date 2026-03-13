import asyncio
import sys
import os
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Add the current directory to sys.path to resolve 'app' imports correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models.asset import Asset, AssetType, AssetClassification, AssetCriticality, CIAValue
from app.models.risk import Risk, RiskCategory, RiskStatus
from app.models.control import Control, ControlType, ControlEffectiveness, ControlStatus, RiskControlMapping

async def verify_risk_engine():
    print("=== GRC RISK ENGINE VERIFICATION ===")
    
    async with SessionLocal() as db:
        # 1. Verify Asset Schema
        asset_result = await db.execute(select(Asset).limit(1))
        asset = asset_result.scalar()
        if asset:
            print(f"SUCCESS: Found Asset '{asset.name}' with type '{asset.type.value}'")
        else:
            print("ERROR: No assets found in database.")
            return

        # 2. Verify Risk Calculation
        risk_result = await db.execute(
            select(Risk).where(Risk.likelihood == 3, Risk.impact == 5)
        )
        risk = risk_result.scalar()
        if risk and risk.risk_score == 15:
            print(f"SUCCESS: Risk '{risk.title}' has correct score {risk.risk_score} (3x5)")
        elif risk:
            print(f"ERROR: Risk '{risk.title}' has INCORRECT score {risk.risk_score}")
        else:
            print("ERROR: Test risk (3x5) not found.")

        # 3. Verify Risk-Asset Link
        if risk and risk.asset_id == asset.id:
            print(f"SUCCESS: Risk '{risk.title}' is correctly linked to Asset '{asset.name}'")
        elif risk:
            print(f"WARNING: Risk '{risk.title}' asset link mismatch or missing")

        # 4. Verify Risk-Control Mapping
        mapping_result = await db.execute(
            select(RiskControlMapping)
            .where(RiskControlMapping.risk_id == risk.id)
            .options(selectinload(RiskControlMapping.control))
        )
        mappings = mapping_result.scalars().all()
        if mappings:
            print(f"SUCCESS: Found {len(mappings)} controls mapped to Risk '{risk.title}'")
            for m in mappings:
                if m.control:
                    print(f"  - Mapped to Control: {m.control.title}")
        else:
            print(f"WARNING: No control mappings found for Risk '{risk.title}'")

    print("=" * 35)
    print("VERIFICATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(verify_risk_engine())
