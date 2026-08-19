import json
import logging
import re
from pathlib import Path
from typing import Any, Iterable, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.models.control_applicability import ControlImplementationStatus

logger = logging.getLogger("grc.control_applicability")

DEFAULT_FRAMEWORK_ID = "iso27001"

FRAMEWORK_CATALOG: dict[str, dict[str, str]] = {
    "iso27001": {
        "name": "ISO 27001",
        "version": "2022",
        "description": "Information Security Management",
    },
    "soc2": {
        "name": "SOC 2",
        "version": "Trust Services Criteria",
        "description": "Service Organization Controls",
    },
    "gdpr": {
        "name": "GDPR",
        "version": "2016/679",
        "description": "General Data Protection Regulation",
    },
    "pcidss": {
        "name": "PCI DSS",
        "version": "4.0",
        "description": "Payment Card Industry Data Security Standard",
    },
}

_FRAMEWORK_ALIASES = {
    "iso": "iso27001",
    "iso27001": "iso27001",
    "isoiec27001": "iso27001",
    "soc": "soc2",
    "soc2": "soc2",
    "socii": "soc2",
    "gdpr": "gdpr",
    "pci": "pcidss",
    "pcidss": "pcidss",
}

_CONTROLS_PATH = Path(__file__).resolve().parents[2] / "data" / "iso27001-controls.json"
_ISO_CONTROLS: list[dict[str, Any]] = []


def _compact_framework_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_framework_id(framework_id: Optional[str]) -> str:
    raw = str(framework_id or DEFAULT_FRAMEWORK_ID).strip()
    compact = _compact_framework_id(raw)
    normalized = _FRAMEWORK_ALIASES.get(compact)
    if not normalized:
        raise ValueError(f"Unknown framework_id: {framework_id}")
    return normalized


def normalize_framework_selection(framework_ids: Optional[Iterable[str]]) -> list[str]:
    if not framework_ids:
        return [DEFAULT_FRAMEWORK_ID]

    normalized: list[str] = []
    for framework_id in framework_ids:
        key = normalize_framework_id(framework_id)
        if key not in normalized:
            normalized.append(key)

    return normalized or [DEFAULT_FRAMEWORK_ID]


def get_framework_display_name(framework_id: str) -> str:
    return FRAMEWORK_CATALOG[framework_id]["name"]


def _load_iso_controls() -> list[dict[str, Any]]:
    global _ISO_CONTROLS
    if not _ISO_CONTROLS:
        with open(_CONTROLS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _ISO_CONTROLS = data.get("controls", [])
    return _ISO_CONTROLS


async def _get_or_create_framework(db: AsyncSession, framework_id: str) -> models.Framework:
    metadata = FRAMEWORK_CATALOG[framework_id]
    aliases = {
        metadata["name"].lower(),
        framework_id.lower(),
        _compact_framework_id(metadata["name"]),
    }

    result = await db.execute(
        select(models.Framework).where(func.lower(models.Framework.name).in_(aliases))
    )
    framework = result.scalars().first()
    if framework:
        return framework

    framework = models.Framework(
        name=metadata["name"],
        version=metadata["version"],
        description=metadata["description"],
    )
    db.add(framework)
    await db.flush()
    return framework


async def _ensure_iso_framework_controls(
    db: AsyncSession,
    framework: models.Framework,
) -> dict[str, models.FrameworkControl]:
    controls = _load_iso_controls()

    result = await db.execute(
        select(models.FrameworkControl).where(models.FrameworkControl.framework_id == framework.id)
    )
    existing = {control.code: control for control in result.scalars().all()}

    for control_data in controls:
        code = control_data.get("annex") or control_data["id"]
        if code in existing:
            continue

        control = models.FrameworkControl(
            framework_id=framework.id,
            code=code,
            title=control_data["title"],
            description=control_data["description"],
            category=control_data.get("clauseId"),
        )
        db.add(control)
        existing[code] = control

    await db.flush()
    return existing


async def initialize_control_applicability_for_framework(
    db: AsyncSession,
    organization_id: UUID,
    framework_id: Optional[str] = DEFAULT_FRAMEWORK_ID,
    overrides: Optional[dict[str, dict[str, Any]]] = None,
    register_with_organization: bool = True,
) -> dict[str, Any]:
    normalized_framework_id = normalize_framework_id(framework_id)
    framework = await _get_or_create_framework(db, normalized_framework_id)

    if register_with_organization:
        org = await db.get(models.Organization, organization_id)
        if not org:
            raise ValueError("Organization not found")
        org_frameworks = normalize_framework_selection(org.compliance_frameworks)
        if normalized_framework_id not in org_frameworks:
            org_frameworks.append(normalized_framework_id)
        org.compliance_frameworks = org_frameworks

    if normalized_framework_id != DEFAULT_FRAMEWORK_ID:
        logger.info(
            "Framework %s registered for org %s; no bundled control catalog is available yet",
            normalized_framework_id,
            organization_id,
        )
        return {
            "framework_id": normalized_framework_id,
            "framework_uuid": str(framework.id),
            "framework_name": framework.name,
            "initialized_count": 0,
            "skipped_count": 0,
            "total_controls": 0,
            "count": 0,
        }

    framework_controls = await _ensure_iso_framework_controls(db, framework)
    control_codes = list(framework_controls.keys())

    existing_result = await db.execute(
        select(models.ControlApplicability)
        .where(models.ControlApplicability.organization_id == organization_id)
        .where(models.ControlApplicability.control_annex.in_(control_codes))
    )
    existing_by_code: dict[str, models.ControlApplicability] = {}
    for applicability in existing_result.scalars().all():
        if applicability.framework_id == framework.id or applicability.framework_id is None:
            existing_by_code[applicability.control_annex] = applicability

    initialized_count = 0
    skipped_count = 0
    overrides = overrides or {}

    for code, framework_control in framework_controls.items():
        existing = existing_by_code.get(code)
        if existing:
            skipped_count += 1
            if existing.framework_id is None:
                existing.framework_id = framework.id
            if existing.framework_control_id is None:
                existing.framework_control_id = framework_control.id
            continue

        override = overrides.get(code, {})
        status_value = override.get("status", ControlImplementationStatus.not_started.value)
        status = ControlImplementationStatus(status_value)

        applicability = models.ControlApplicability(
            organization_id=organization_id,
            framework_id=framework.id,
            framework_control_id=framework_control.id,
            control_annex=code,
            is_applicable=override.get("is_applicable", True),
            status=status,
            justification=override.get("justification"),
            responsible_id=override.get("responsible_id"),
            notes=override.get("notes"),
        )
        db.add(applicability)
        initialized_count += 1

    await db.flush()
    logger.info(
        "Initialized %s %s controls for org %s; skipped %s existing controls",
        initialized_count,
        framework.name,
        organization_id,
        skipped_count,
    )

    return {
        "framework_id": normalized_framework_id,
        "framework_uuid": str(framework.id),
        "framework_name": framework.name,
        "initialized_count": initialized_count,
        "skipped_count": skipped_count,
        "total_controls": len(framework_controls),
        "count": initialized_count,
    }
