from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import enum
from .base import Base


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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # File metadata
    file_name = Column(String, nullable=False)
    file_url = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)  # pdf, docx, etc.

    # Processing
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(
        SAEnum(DocumentAnalysisStatus),
        default=DocumentAnalysisStatus.pending,
        nullable=False,
    )

    # AI-classified document category (policy, procedure, architecture, log, certificate, etc.)
    document_category = Column(String, nullable=True)

    # Full extracted text (stored for re-analysis)
    extracted_text = Column(Text, nullable=True)

    # Structured AI output
    # Example: {"summary": "...", "key_findings": [...], "risk_areas": [...]}
    analysis_result = Column(JSONB, nullable=True)

    # List of controls found implemented with confidence
    # Example: [{"control_annex": "5.1", "title": "...", "confidence": 85.2, "excerpt": "..."}]
    implemented_controls = Column(JSONB, nullable=True)

    # List of controls that should be present but are missing
    # Example: [{"control_annex": "8.12", "title": "Data Leakage Prevention", "reason": "..."}]
    missing_controls = Column(JSONB, nullable=True)

    # Extracted security practices
    # Example: [{"practice": "MFA enforced for admins", "related_controls": ["5.17", "8.5"]}]
    security_practices = Column(JSONB, nullable=True)

    # Optional link to Evidence — when the document also serves as audit evidence
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    evidence = relationship("Evidence", foreign_keys=[evidence_id])
