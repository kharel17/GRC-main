"""
Starter Policy Generator Service.
Synthesizes contextual baseline security policies tailored to an organization's
metadata (industry, infrastructure, data types) and indexes them into Qdrant + DB.
"""
from typing import List, Dict, Any, Optional, Callable, TypedDict
from uuid import UUID
import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import models
from app.models.document_analysis import DocumentAnalysisStatus
from app.ingestion.extractor import PageContent
from app.ingestion.chunker import chunk_document
from app.services.ai_service import ai_service
from app.services.document_analyzer import _run_document_analysis_async
from app.services.vector_store import vector_store

logger = logging.getLogger("grc.policy_generator")


def _generate_access_control_policy(org_name: str, industry: str, infrastructure: str) -> str:
    return f"""# {org_name} - Access Control & Authentication Policy

## 1. Purpose & Scope
This policy establishes mandatory access control principles for {org_name}, operating within the {industry} sector. It applies to all employees, contractors, third-party vendors, and automated systems accessing organizational data and infrastructure, including: {infrastructure}.

## 2. Principle of Least Privilege
- Access rights are granted based strictly on the principle of least privilege and need-to-know.
- Role-Based Access Control (RBAC) must be enforced across all cloud services, server environments, and database layers.
- Default access permissions for all newly created accounts shall be set to 'Deny All'.

## 3. User Authentication & Credentials (ISO 27001 A.5.17, A.8.5)
- Multi-Factor Authentication (MFA) is strictly mandatory for all users accessing production systems, email, VPNs, and administrative interfaces.
- Passwords must be at least 14 characters in length and include uppercase, lowercase, numerical, and special characters.
- Shared, generic, or group accounts are prohibited. Every user must have a unique identifier.
- Sessions shall automatically lock or expire after 15 minutes of user inactivity.

## 4. Privileged Access Management (ISO 27001 A.8.2)
- Administrative privileges must only be granted to authorized personnel requiring them for operational duties.
- Privileged operations must be logged and monitored.
- Separate accounts must be maintained for administrative activities and routine daily tasks.

## 5. Provisioning & Deprovisioning (ISO 27001 A.5.18)
- Access requests require formal approval from the designated department manager and system owner.
- Upon employee resignation or termination, all user access rights and physical tokens must be revoked within 2 hours.
- Formal user access reviews must be conducted at least quarterly.
"""


def _generate_incident_response_plan(org_name: str, industry: str, infrastructure: str, data_types: str) -> str:
    return f"""# {org_name} - Information Security Incident Management Plan

## 1. Purpose & Objectives
The purpose of this plan is to ensure a fast, coordinated, and effective response to information security events and incidents affecting {org_name}. It protects the confidentiality, integrity, and availability of infrastructure ({infrastructure}) and sensitive data ({data_types}).

## 2. Incident Classification & Severity (ISO 27001 A.5.25)
- **Critical (P1)**: Active security breach, unauthorized access to sensitive {data_types}, or complete service outage.
- **High (P2)**: Severe malware outbreak, compromised privileged credentials, or widespread system disruption.
- **Medium (P3)**: Suspected policy violation, localized phishing attempts, or unauthorized configuration changes.
- **Low (P4)**: Minor non-compliance events, isolated workstation alerts, or benign scanning activity.

## 3. Incident Response Team (IRT) & Escalation (ISO 27001 A.5.24)
- An Incident Response Lead (IRL) shall command and direct all response activities.
- Technical specialists shall investigate infrastructure anomalies and contain active compromises.
- Executive management and Legal Counsel must be notified of P1 and P2 incidents within 1 hour.

## 4. Containment, Eradication & Recovery (ISO 27001 A.5.26)
- Affected endpoints or virtual machines must be isolated immediately from the production network.
- Malicious artifacts, backdoors, and unauthorized credentials must be removed and revoked before system restoration.
- Systems shall be restored from verified, tamper-proof backups and subjected to enhanced monitoring for 72 hours.

## 5. Evidence Preservation & Post-Incident Review (ISO 27001 A.5.27, A.5.28)
- Chain-of-custody must be maintained for all digital evidence, memory dumps, and forensic disk images.
- A blameless Post-Mortem and Root Cause Analysis (RCA) must be finalized within 5 business days of incident closure.
- Action items identified during review shall be tracked to completion in the remediation ticket register.
"""


def _generate_data_protection_policy(org_name: str, industry: str, infrastructure: str, data_types: str) -> str:
    return f"""# {org_name} - Data Protection & Cryptography Policy

## 1. Scope & Applicability
This policy governs the classification, handling, storage, and cryptographic protection of all information assets owned, operated, or processed by {org_name}. Particular emphasis is placed on sensitive records, including: {data_types}.

## 2. Information Classification Levels (ISO 27001 A.5.12, A.5.13)
- **Restricted**: Highly confidential data (e.g., cryptographic keys, credentials, financial transaction data). Strictest access controls required.
- **Confidential**: Internal business information, customer records, and protected employee data ({data_types}). Access restricted to authorized personnel.
- **Internal**: General business operational communications, internal guides, and memos.
- **Public**: Marketing materials, public website content, and approved press releases.

## 3. Cryptographic Controls (ISO 27001 A.8.24)
- **Data at Rest**: All databases, cloud storage buckets, file shares, and mobile devices storing Confidential or Restricted information across {infrastructure} must be encrypted using AES-256 or equivalent approved cipher.
- **Data in Transit**: All external and inter-service communications across untrusted networks must enforce TLS 1.3 (or TLS 1.2 minimum). Unencrypted protocols (HTTP, Telnet, FTP) are strictly prohibited.
- Storage of unencrypted sensitive {data_types} is a critical policy violation.

## 4. Key Management Lifecycle
- Encryption keys must be generated using cryptographically secure pseudorandom number generators (CSPRNG).
- Master encryption keys must reside in dedicated Hardware Security Modules (HSM) or secure cloud Key Management Services (KMS).
- Keys must be rotated at least annually or immediately upon suspicion of compromise.

## 5. Secure Disposal & Data Retention
- Information must not be retained beyond its legally or operationally mandated retention period.
- Physical media and digital assets scheduled for decommissioning must undergo cryptographic erasure or certified physical destruction.
"""


class BaselinePolicyTemplate(TypedDict):
    template_key: str
    title: str
    file_name: str
    category: str
    mapped_controls: List[str]
    generate_content: Callable[..., str]


BASELINE_POLICY_TEMPLATES: List[BaselinePolicyTemplate] = [
    {
        "template_key": "access_control",
        "title": "Access Control & Authentication Policy",
        "file_name": "Access_Control_Policy.txt",
        "category": "policy",
        "mapped_controls": ["A.5.15", "A.5.17", "A.5.18", "A.8.2", "A.8.5"],
        "generate_content": lambda org_name, industry="Technology", infrastructure="Cloud", data_types="": _generate_access_control_policy(org_name, industry, infrastructure),
    },
    {
        "template_key": "incident_response",
        "title": "Incident Management & Response Plan",
        "file_name": "Incident_Response_Plan.txt",
        "category": "procedure",
        "mapped_controls": ["A.5.24", "A.5.25", "A.5.26", "A.5.27", "A.5.28"],
        "generate_content": lambda org_name, industry="Technology", infrastructure="Cloud", data_types="Data": _generate_incident_response_plan(org_name, industry, infrastructure, data_types),
    },
    {
        "template_key": "data_protection",
        "title": "Data Protection & Cryptography Policy",
        "file_name": "Data_Protection_Policy.txt",
        "category": "policy",
        "mapped_controls": ["A.5.12", "A.5.13", "A.8.24"],
        "generate_content": lambda org_name, industry="Technology", infrastructure="Cloud", data_types="Data": _generate_data_protection_policy(org_name, industry, infrastructure, data_types),
    },
]


async def generate_starter_policies(
    db: AsyncSession,
    organization_id: UUID,
    user_id: UUID,
    org_name: str,
    industry: Optional[str] = None,
    infrastructure: Optional[str] = None,
    data_types: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Synthesizes the 3 baseline security policies for an organization,
    persists them as DocumentAnalysis records in PostgreSQL,
    chunks them into Qdrant (grc_doc_chunks), and executes control mapping.
    """
    industry_str = industry or "Technology"
    infra_str = infrastructure or "Cloud & Hybrid Systems"
    data_str = data_types or "Customer Records & Operations Data"

    starter_definitions = [
        {
            "title": t["title"],
            "file_name": t["file_name"],
            "category": t["category"],
            "text": t["generate_content"](org_name, industry_str, infra_str, data_str),
        }
        for t in BASELINE_POLICY_TEMPLATES
    ]

    generated_results = []

    # Ensure AI service is ready for embeddings
    if not ai_service.is_ready:
        try:
            ai_service.initialize()
        except Exception as init_err:
            logger.warning(f"ai_service initialization warning during starter policy generation: {init_err}")

    for policy_def in starter_definitions:
        text = policy_def["text"]
        doc_id = uuid.uuid4()

        # 1. Run analysis to identify mapped controls and security practices
        analysis_data: Dict[str, Any] = {}
        try:
            analysis_data = await _run_document_analysis_async(text)
        except Exception as analysis_err:
            logger.warning(f"Control mapping failed for starter policy '{policy_def['title']}': {analysis_err}")
            analysis_data = {
                "document_category": policy_def["category"],
                "implemented_controls": [],
                "missing_controls": [],
                "security_practices": [],
                "summary": f"Baseline {policy_def['title']} generated for {org_name}.",
            }

        # 2. Persist DocumentAnalysis row
        doc_analysis = models.DocumentAnalysis(
            id=doc_id,
            organization_id=organization_id,
            file_name=policy_def["file_name"],
            file_url=None,
            file_size=len(text.encode("utf-8")),
            file_type="txt",
            uploaded_by=user_id,
            status=DocumentAnalysisStatus.completed,
            document_category=policy_def["category"],
            extracted_text=text,
            analysis_result=analysis_data,
            implemented_controls=analysis_data.get("implemented_controls", []),
            missing_controls=analysis_data.get("missing_controls", []),
            security_practices=analysis_data.get("security_practices", []),
            created_at=datetime.now(timezone.utc),
        )
        db.add(doc_analysis)

        # 3. Chunk and index into Qdrant grc_doc_chunks (scoped by organization_id)
        chunks_indexed = 0
        try:
            pages = [PageContent(page_number=1, raw_text=text)]
            chunks = chunk_document(
                pages=pages,
                document_id=str(doc_id),
                org_id=str(organization_id),
                target_token_size=300,
                overlap_ratio=0.10,
            )
            if chunks and vector_store.is_ready:
                chunk_texts = [c.text for c in chunks]
                embeddings = ai_service._embed_texts(chunk_texts)
                await vector_store.upsert_chunks(chunks, embeddings)
                chunks_indexed = len(chunks)
                logger.info(f"Vector Store: Indexed {chunks_indexed} starter chunks for '{policy_def['title']}'")
        except Exception as vs_err:
            logger.warning(f"Vector Store chunk indexing warning for '{policy_def['title']}': {vs_err}")

        generated_results.append({
            "id": str(doc_id),
            "title": policy_def["title"],
            "file_name": policy_def["file_name"],
            "category": policy_def["category"],
            "chunks_indexed": chunks_indexed,
            "controls_mapped_count": len(analysis_data.get("implemented_controls", [])),
        })

    await db.commit()
    logger.info(f"Successfully generated and indexed {len(generated_results)} starter policies for org {org_name} ({organization_id})")
    return generated_results
