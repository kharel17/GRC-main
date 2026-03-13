"""
Compliance Service — Core engine for Statement of Applicability (SoA) and Compliance Scoring.
"""
import logging
from uuid import UUID
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app import models
from app.models.control_applicability import ControlImplementationStatus
from app.services.gap_analysis_service import _ISO_CONTROLS

logger = logging.getLogger("grc.compliance")

class SoAItem:
    def __init__(
        self, 
        control_annex: str, 
        title: str, 
        is_applicable: bool, 
        status: str, 
        justification: Optional[str] = None,
        responsible_name: Optional[str] = None,
        notes: Optional[str] = None
    ):
        self.control_annex = control_annex
        self.title = title
        self.is_applicable = is_applicable
        self.status = status
        self.justification = justification
        self.responsible_name = responsible_name
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            "control_annex": self.control_annex,
            "title": self.title,
            "is_applicable": self.is_applicable,
            "status": self.status,
            "justification": self.justification,
            "responsible_name": self.responsible_name,
            "notes": self.notes
        }

class ComplianceService:
    @staticmethod
    async def get_soa(db: AsyncSession, organization_id: UUID) -> List[dict]:
        """
        Generates the Statement of Applicability (SoA) for an organization.
        """
        # Fetch all applicability records
        stmt = (
            select(models.ControlApplicability, models.User.full_name)
            .outerjoin(models.User, models.ControlApplicability.responsible_id == models.User.id)
            .where(models.ControlApplicability.organization_id == organization_id)
        )
        result = await db.execute(stmt)
        ca_data = result.all()
        
        ca_map = {ca.control_annex: (ca, name) for ca, name in ca_data}
        
        soa = []
        # Use the master control list
        for ctrl in _ISO_CONTROLS:
            annex = ctrl["id"]
            ca_record, resp_name = ca_map.get(annex, (None, None))
            
            if ca_record:
                item = SoAItem(
                    control_annex=annex,
                    title=ctrl["title"],
                    is_applicable=ca_record.is_applicable,
                    status=ca_record.status.value,
                    justification=ca_record.justification,
                    responsible_name=resp_name,
                    notes=ca_record.notes
                )
            else:
                # Default if not initialized (though seeding should prevent this)
                item = SoAItem(
                    control_annex=annex,
                    title=ctrl["title"],
                    is_applicable=True,
                    status="not_started"
                )
            soa.append(item.to_dict())
            
        return soa

    @staticmethod
    async def get_compliance_score(db: AsyncSession, organization_id: UUID) -> Dict[str, Any]:
        """
        Calculates the compliance score and provides a detailed breakdown.
        """
        stmt = (
            select(
                func.count().label("total"),
                func.count().filter(models.ControlApplicability.is_applicable == True).label("applicable"),
                func.count().filter(models.ControlApplicability.status == ControlImplementationStatus.implemented).label("implemented"),
                func.count().filter(models.ControlApplicability.status == ControlImplementationStatus.in_progress).label("in_progress"),
                func.count().filter(models.ControlApplicability.status == ControlImplementationStatus.not_started).label("not_started"),
                func.count().filter(models.ControlApplicability.is_applicable == False).label("not_applicable")
            )
            .where(models.ControlApplicability.organization_id == organization_id)
        )
        result = await db.execute(stmt)
        stats = result.one()
        
        score = round((stats.implemented / stats.applicable * 100), 1) if stats.applicable > 0 else 0
        
        return {
            "score": score,
            "implemented": stats.implemented,
            "in_progress": stats.in_progress,
            "not_started": stats.not_started,
            "not_applicable": stats.not_applicable,
            "applicable_total": stats.applicable,
            "total_controls": stats.total
        }

compliance_service = ComplianceService()
