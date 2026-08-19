"""
Dashboard Service — Aggregates analytics across compliance, risks, and tickets for the main dashboard.
"""
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.models import Ticket, Risk, AuditLog, User, TicketStatus
from app.services.compliance_service import compliance_service

class DashboardService:
    @staticmethod
    async def get_dashboard_summary(db: AsyncSession, organization_id: UUID) -> Dict[str, Any]:
        """
        Aggregates summary data for the dashboard.
        """
        # 1. Compliance Summary
        compliance_summary = await compliance_service.get_compliance_score(db, organization_id)
        
        # 2. Risk Summary (by severity)
        # Severity mapping: Critical >= 20, High >= 15, Medium >= 8, Low < 8
        risk_stmt = (
            select(Risk.risk_score)
            .where(Risk.organization_id == organization_id)
        )
        risk_result = await db.execute(risk_stmt)
        risk_scores = risk_result.scalars().all()
        
        risk_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": len(risk_scores)
        }
        for score in risk_scores:
            if score >= 20:
                risk_counts["critical"] += 1
            elif score >= 15:
                risk_counts["high"] += 1
            elif score >= 8:
                risk_counts["medium"] += 1
            else:
                risk_counts["low"] += 1
                
        # 3. Ticket Summary (by status)
        ticket_stmt = (
            select(
                func.count().filter(Ticket.status == TicketStatus.open).label("open_tickets"),
                func.count().filter(Ticket.status == TicketStatus.in_review).label("in_progress"),
                func.count().filter(Ticket.status == TicketStatus.resolved).label("resolved"),
                func.count().label("total")
            )
            .where(Ticket.organization_id == organization_id)
        )
        ticket_result = await db.execute(ticket_stmt)
        ticket_stats = ticket_result.one()
        
        # 4. Recent Activity — scoped to users in this organization
        activity_stmt = (
            select(AuditLog)
            .join(User, AuditLog.user_id == User.id)
            .where(User.organization_id == organization_id)
            .order_by(desc(AuditLog.timestamp))
            .limit(5)
        )
        activity_result = await db.execute(activity_stmt)
        recent_logs = activity_result.scalars().all()
        
        formatted_activity = []
        for log in recent_logs:
            formatted_activity.append({
                "id": str(log.id),
                "action": log.action.value,
                "entity_type": log.entity_type.value,
                "entity_name": log.entity_name,
                "description": log.description,
                "timestamp": log.timestamp.isoformat()
            })

        return {
            "compliance": compliance_summary,
            "risks": risk_counts,
            "tickets": {
                "open": ticket_stats.open_tickets,
                "in_progress": ticket_stats.in_progress,
                "resolved": ticket_stats.resolved,
                "total": ticket_stats.total
            },
            "recent_activity": formatted_activity
        }

dashboard_service = DashboardService()
