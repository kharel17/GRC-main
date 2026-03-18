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
        With dynamic status calculation based on evidence.
        """
        from app.models.evidence import Evidence, EvidenceControlMatch, EvidenceStatus
        from sqlalchemy import func

        # 1. Fetch evidence counts per control code (annex)
        counts_stmt = (
            select(
                EvidenceControlMatch.control_id,
                func.count(Evidence.id).label("total"),
                func.count(Evidence.id).filter(Evidence.status == EvidenceStatus.verified).label("verified")
            )
            .join(Evidence, EvidenceControlMatch.evidence_id == Evidence.id)
            .where(Evidence.organization_id == organization_id)
            .group_by(EvidenceControlMatch.control_id)
        )
        counts_res = await db.execute(counts_stmt)
        evidence_stats = {row.control_id: (row.total, row.verified) for row in counts_res.all()}

        # 2. Fetch all applicability records for the org
        stmt = (
            select(models.ControlApplicability, models.User.full_name)
            .outerjoin(models.User, models.ControlApplicability.responsible_id == models.User.id)
            .where(models.ControlApplicability.organization_id == organization_id)
        )
        result = await db.execute(stmt)
        ca_data = result.all()
        
        ca_map = {ca.control_annex: (ca, name) for ca, name in ca_data}
        
        soa = []
        # Use the master control list (93 controls)
        for ctrl in _ISO_CONTROLS:
            annex = ctrl["id"]
            ca_record, resp_name = ca_map.get(annex, (None, None))
            total_ev, verified_ev = evidence_stats.get(annex, (0, 0))
            
            # DYNAMIC STATUS CALCULATION
            # Default to record status if explicitly set to 'not_applicable'
            if ca_record and ca_record.status == models.control_applicability.ControlImplementationStatus.not_applicable:
                derived_status = "not_applicable"
            elif verified_ev > 0:
                derived_status = "implemented"
            elif total_ev > 0:
                derived_status = "in_progress"
            else:
                derived_status = "not_started"

            soa.append({
                "control_annex": annex,
                "control_title": ctrl["title"],
                "control_description": ctrl["description"],
                "clause_id": ctrl["clauseId"],
                "is_applicable": ca_record.is_applicable if ca_record else True,
                "status": derived_status,
                "justification": ca_record.justification if ca_record else None,
                "responsible_id": str(ca_record.responsible_id) if ca_record and ca_record.responsible_id else None,
                "responsible_name": resp_name,
                "evidence_count": total_ev,
                "notes": ca_record.notes if ca_record else None
            })
            
        return soa

    @staticmethod
    async def get_compliance_score(db: AsyncSession, organization_id: UUID) -> Dict[str, Any]:
        """
        Calculates the compliance score and provides a detailed breakdown.
        DYNAMIC: Considers a control 'implemented' if it has at least one verified evidence.
        """
        from app.models.evidence import Evidence, EvidenceControlMatch, EvidenceStatus
        from sqlalchemy import func

        # 1. Get verified evidence counts per control
        verified_stmt = (
            select(EvidenceControlMatch.control_id)
            .join(Evidence, EvidenceControlMatch.evidence_id == Evidence.id)
            .where(Evidence.organization_id == organization_id)
            .where(Evidence.status == EvidenceStatus.verified)
            .distinct()
        )
        verified_res = await db.execute(verified_stmt)
        verified_control_ids = {row[0] for row in verified_res.all()}

        # 2. Get all applicability records
        stmt = (
            select(models.ControlApplicability)
            .where(models.ControlApplicability.organization_id == organization_id)
        )
        result = await db.execute(stmt)
        ca_records = result.scalars().all()

        total = len(_ISO_CONTROLS)
        applicable = 0
        implemented = 0
        in_progress = 0
        not_applicable = 0

        # Create a map for quick lookup
        ca_map = {ca.control_annex: ca for ca in ca_records}

        for ctrl in _ISO_CONTROLS:
            annex = ctrl["id"]
            ca = ca_map.get(annex)
            
            is_applicable = ca.is_applicable if ca else True
            
            if not is_applicable:
                not_applicable += 1
                continue
            
            applicable += 1
            if annex in verified_control_ids:
                implemented += 1
            else:
                # We'd need total evidence (not just verified) to distinguish in_progress
                # But for the core score, 'implemented' is what matters.
                pass

        score = round((implemented / applicable * 100), 1) if applicable > 0 else 0
        
        return {
            "score": score,
            "implemented": implemented,
            "in_progress": in_progress, # Simplified for now
            "not_started": applicable - implemented - in_progress,
            "not_applicable": not_applicable,
            "applicable_total": applicable,
            "total_controls": total
        }

compliance_service = ComplianceService()
