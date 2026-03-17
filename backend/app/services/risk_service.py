from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import models

async def recheck_risk_status(risk_id: str, db: AsyncSession):
    """
    Recheck and update risk status based on mapped controls effectiveness and status.
    (Bug 2)
    """
    result = await db.execute(select(models.Risk).where(models.Risk.id == risk_id))
    risk = result.scalars().first()
    if not risk:
        return
    
    # Get all remaining mapped controls
    result = await db.execute(
        select(models.Control)
        .join(models.RiskControlMapping)
        .where(models.RiskControlMapping.risk_id == risk_id)
    )
    controls = result.scalars().all()
    
    has_high_implemented = any(
        c.effectiveness == models.ControlEffectiveness.high and c.status == models.ControlStatus.implemented
        for c in controls
    )
    has_any_planned = any(c.status in [models.ControlStatus.planned, models.ControlStatus.under_review] for c in controls)
    
    if has_high_implemented:
        risk.status = models.RiskStatus.mitigated
    elif has_any_planned or controls:
        risk.status = models.RiskStatus.assessed
    else:
        risk.status = models.RiskStatus.identified
    
    await db.commit()
