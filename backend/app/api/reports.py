from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Any
import datetime
from jinja2 import Environment, FileSystemLoader
import os

from app.api import deps
from app import models

router = APIRouter()

@router.get("/")
async def list_reports(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """List available report types."""
    return [
        {"id": "risk-summary", "title": "Risk Summary Report", "description": "Overview of all risks and their scores"},
        {"id": "compliance-status", "title": "Compliance Status Report", "description": "Current compliance posture across frameworks"},
    ]

# Setup Jinja2 Environment pointing to the templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

@router.get("/{report_type}/export", response_class=HTMLResponse)
async def export_report(
    report_type: str,
    db: AsyncSession = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate an HTML report based on the requested report type.
    We are temporarily returning HTML. In the future, this HTML
    will be converted to PDF using a library like WeasyPrint.
    """
    
    generated_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_by = current_user.full_name or current_user.email
    
    if report_type == "risk-summary":
        template = env.get_template("risk_summary.html")
        
        # Fetch all risks with their categories and owners
        result = await db.execute(
            select(models.Risk)
            .options(selectinload(models.Risk.category))
            .options(selectinload(models.Risk.owner))
        )
        risks_data = result.scalars().all()
        
        total_risks = len(risks_data)
        high_risks = sum(1 for r in risks_data if r.risk_score >= 15)
        average_score = sum(r.risk_score for r in risks_data) / total_risks if total_risks > 0 else 0
        
        # Format the data for the template
        formatted_risks = []
        for r in risks_data:
            formatted_risks.append({
                "title": r.title,
                "category": r.category.name if r.category else "Unknown",
                "score": r.risk_score,
                "status": r.status.value.capitalize(),
                "owner": r.owner.full_name if r.owner else "Unassigned"
            })
            
        html_content = template.render(
            report_title="Risk Summary Report",
            generated_date=generated_date,
            generated_by=generated_by,
            total_risks=total_risks,
            average_score=round(average_score, 1),
            high_risks_count=high_risks,
            risks=formatted_risks
        )
        
        return HTMLResponse(content=html_content)
        
    elif report_type == "compliance-status":
        template = env.get_template("compliance_status.html")
        
        # NOTE: Fetching Compliance data. As we only inspected Risks earlier,
        # we assume a basic ComplianceItem model exists based on the mock data.
        # This will need to be adjusted if the model structure differs.
        try:
            result = await db.execute(select(models.ComplianceItem))
            items_data = result.scalars().all()
            
            total_items = len(items_data)
            compliant_count = sum(1 for i in items_data if i.status.value == 'compliant')
            progress_count = sum(1 for i in items_data if i.status.value == 'in_progress')
            gap_count = total_items - compliant_count - progress_count
            compliance_percentage = int((compliant_count / total_items) * 100) if total_items > 0 else 0
            
            formatted_items = []
            for i in items_data:
                formatted_items.append({
                    "requirementId": i.framework_req_id if hasattr(i, 'framework_req_id') else "N/A",
                    "title": i.title,
                    "status": i.status.value.capitalize(),
                    "dueDate": i.due_date.strftime("%Y-%m-%d") if i.due_date else "None",
                    "owner": "Team" # Placeholder until owner relation is verified
                })
        except Exception as e:
            # Fallback if ComplianceItem model is not fully mapped yet
            compliance_percentage = 0
            total_items = 0
            compliant_count = 0
            progress_count = 0
            gap_count = 0
            formatted_items = []
            print(f"Error fetching compliance data: {e}")

        html_content = template.render(
            report_title="Compliance Status Report",
            generated_date=generated_date,
            generated_by=generated_by,
            framework_name="Multiple Frameworks",
            compliance_percentage=compliance_percentage,
            total_items=total_items,
            compliant_count=compliant_count,
            progress_count=progress_count,
            gap_count=gap_count,
            items=formatted_items
        )
        
        return HTMLResponse(content=html_content)
        
    else:
        raise HTTPException(status_code=404, detail="Report type not supported yet.")
