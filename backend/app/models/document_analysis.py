from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from typing import Optional, Any
import uuid
import enum
from .base import Base, utc_now


class DocumentAnalysisStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DocumentAnalysis(Base):
    """
    Stores AI analysis results for uploaded security documentation (Step 3).
    
    When a user uploads a policy, procedure, or architecture doc, the AI extracts:
    - Implemented controls (with confidence scores)
    - Missing controls
    - Security practices found in the document
    
    Optionally linked to an Evidence record when the same document also serves
    as compliance proof.
    """
    __tablename__ = "document_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # File metadata
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # pdf, docx, etc.

    # Processing
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[DocumentAnalysisStatus] = mapped_column(
        SAEnum(DocumentAnalysisStatus),
        default=DocumentAnalysisStatus.pending,
        nullable=False,
    )

    # AI-classified document category (policy, procedure, architecture, log, certificate, etc.)
    document_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Full extracted text (stored for re-analysis)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured AI output
    # Example: {"summary": "...", "key_findings": [...], "risk_areas": [...]}
    analysis_result: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    # List of controls found implemented with confidence
    # Example: [{"control_annex": "5.1", "title": "...", "confidence": 85.2, "excerpt": "..."}]
    implemented_controls: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    # List of controls that should be present but are missing
    # Example: [{"control_annex": "8.12", "title": "Data Leakage Prevention", "reason": "..."}]
    missing_controls: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    # Extracted security practices
    # Example: [{"practice": "MFA enforced for admins", "related_controls": ["5.17", "8.5"]}]
    security_practices: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    # Optional link to Evidence — when the document also serves as audit evidence
    evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    evidence = relationship("Evidence", foreign_keys=[evidence_id])
