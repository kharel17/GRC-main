"""
AI Service – Hybrid AI Strategy: Local NLP Embeddings + Gemini Generation.

Primary:  NLP (all-MiniLM-L6-v2) for all embeddings and semantic matching.
Primary:  Google Gemini API (gemini-1.5-flash) for advanced text generation.

Embeddings are always computed locally for speed and reliability. Gemini is used
for deeper document analysis and risk scoring whenever a key is present.
"""

import json
import logging
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

from app.config import settings

from google import genai
from google.genai import types
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("grc.ai")

# ---------------------------------------------------------------------------
# Data classes for AI results
# ---------------------------------------------------------------------------

class ControlMatch:
    """Represents a single AI-matched ISO 27001 control."""
    def __init__(self, control_id: str, annex: str, title: str, description: str,
                 clause_id: str, confidence: float):
        self.control_id = control_id
        self.annex = annex
        self.title = title
        self.description = description
        self.clause_id = clause_id
        self.confidence = round(confidence * 100, 1)  # 0-100 percentage

    def to_dict(self) -> dict:
        return {
            "control_id": self.control_id,
            "annex": self.annex,
            "title": self.title,
            "description": self.description,
            "clause_id": self.clause_id,
            "confidence": self.confidence,
        }


class EvidenceAnalysisResult:
    """Full result of analyzing an evidence document."""
    def __init__(self, category: str, matched_controls: list[ControlMatch],
                 summary: str):
        self.category = category
        self.matched_controls = matched_controls
        self.summary = summary

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "matched_controls": [m.to_dict() for m in self.matched_controls],
            "summary": self.summary,
        }


class DocumentAnalysisAIResult:
    """Full AI analysis of a security document for Step 3."""
    def __init__(self, summary: str, category: str, 
                 implemented_controls: list[dict], 
                 missing_controls: list[dict], 
                 security_practices: list[dict]):
        self.summary = summary
        self.category = category
        self.implemented_controls = implemented_controls
        self.missing_controls = missing_controls
        self.security_practices = security_practices

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "category": self.category,
            "implemented_controls": self.implemented_controls,
            "missing_controls": self.missing_controls,
            "security_practices": self.security_practices
        }


class RiskSuggestion:
    """AI-suggested risk scoring."""
    def __init__(self, likelihood: int, impact: int, risk_score: int,
                 reasoning: str, related_controls: list[str]):
        self.likelihood = likelihood
        self.impact = impact
        self.risk_score = risk_score
        self.reasoning = reasoning
        self.related_controls = related_controls

    def to_dict(self) -> dict:
        return {
            "likelihood": self.likelihood,
            "impact": self.impact,
            "risk_score": self.risk_score,
            "reasoning": self.reasoning,
            "related_controls": self.related_controls,
        }


# ---------------------------------------------------------------------------
# Evidence category keywords (used by both engines)
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "policy": ["policy", "policies", "guideline", "framework", "standard", "directive"],
    "procedure": ["procedure", "process", "workflow", "step-by-step", "instruction", "sop"],
    "log": ["log", "audit trail", "event", "syslog", "access log", "monitoring"],
    "certificate": ["certificate", "certification", "accreditation", "iso", "soc", "attestation"],
    "report": ["report", "assessment", "review", "analysis", "finding", "summary"],
    "training": ["training", "awareness", "education", "course", "workshop", "session"],
    "contract": ["contract", "agreement", "nda", "sla", "terms", "vendor", "supplier"],
    "configuration": ["configuration", "config", "settings", "baseline", "hardening", "firewall"],
}


# ---------------------------------------------------------------------------
# PDF Text Extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from a PDF/document file's bytes using unified extractor with OCR fallback."""
    # 1. Try unified extractor (PyMuPDF + Tesseract OCR + DOCX + plain text)
    try:
        from app.ingestion.extractor import extract_text_from_bytes
        text = extract_text_from_bytes(file_bytes, "document.pdf")
        if text.strip():
            return text.strip()
    except Exception as e:
        logger.warning(f"Unified extractor failed ({e}), trying fallback handlers")

    # 2. Fallback: PyPDF2 / pypdf with strict=False
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(BytesIO(file_bytes), strict=False)
        pages_text: list[str] = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t.strip())
        extracted = "\n\n".join(pages_text)
        if extracted.strip():
            return extracted
    except Exception as e:
        logger.warning(f"PyPDF2 fallback extraction failed: {e}")

    # 3. Fallback: docx format parser
    try:
        import docx
        doc = docx.Document(BytesIO(file_bytes))
        full_text = [p.text for p in doc.paragraphs if p.text.strip()]
        if full_text:
            return "\n\n".join(full_text)
    except Exception:
        pass

    # 4. Fallback: UTF-8 / Latin-1 text decode for plain text / markdown / logs
    try:
        decoded = file_bytes.decode('utf-8', errors='ignore')
        # Check if file has readable text characters
        printable_ratio = sum(1 for c in decoded if c.isprintable() or c in '\n\r\t') / max(len(decoded), 1)
        if printable_ratio > 0.85 and len(decoded.strip()) > 10:
            return decoded.strip()
    except Exception:
        pass

    return ""


# Domain synonyms and cross-standard terminology to resolve sub-clause ambiguity
ISO_DOMAIN_SYNONYMS: dict[str, str] = {
    "7.1": "Physical security perimeters, biometric access control and CCTV monitoring of server room perimeters, physical perimeter boundaries, surveillance.",
    "7.2": "Physical entry controls, building doors, entry keycards, visitor badge reception, turnstiles.",
    "7.13": "Equipment maintenance, server hardware maintenance outsourced to certified vendor, hardware servicing.",
    "5.15": "Access control policy, role-based access control, RBAC, access restrictions.",
    "5.17": "Authentication information, user password complexity rules, secret authentication credentials, password requirements.",
    "5.24": "Incident management planning, security incident response procedure, incident reporting timelines.",
    "5.29": "Information security during disruption, business continuity, disaster recovery quarterly drills, continuity testing.",
    "6.1": "Screening, pre-employment background screening, HR security, background check verification.",
    "6.5": "Responsibilities after termination or change of employment, contractors signing confidentiality agreements upon offboarding, NDAs.",
    "6.6": "Confidentiality or non-disclosure agreements, NDAs, contractor confidentiality.",
    "8.5": "Secure authentication, password complexity, multi-factor authentication MFA, login credentials.",
    "8.8": "Management of technical vulnerabilities, automated vulnerability scanning frequency, patch management windows.",
    "8.15": "Logging, audit logging, system activity logs, event recording.",
    "8.16": "Monitoring activities, SIEM system aggregates events from firewalls and triggers alerts on abnormal behavior, network monitoring.",
    "8.22": "Web filtering, network isolation, AWS security groups isolating test environments, segmenting environments.",
    "8.24": "Use of cryptography, cryptographic key management rules, encryption algorithms, data encryption at rest and in transit.",
    "8.25": "Secure development life cycle, developers receive secure coding certification, SDLC guidelines.",
    "8.28": "Secure coding, developers review pull requests and verify code security before merging, peer code review.",
    "8.31": "Separation of development, test and production environments, AWS security groups isolation.",
    "8.32": "Change management, system administrators use Git repositories to track infrastructure-as-code version changes, PR approvals.",
}


class AIService:
    """
    Hybrid AI engine: Gemini API (primary) with local NLP fallback.

    On initialization:
      1. Loads ISO 27001 control data
      2. Tries to init Gemini client (if GEMINI_API_KEY is set)
      3. Loads local SentenceTransformer model as fallback
      4. Pre-computes control embeddings using whichever engine is available

    On each request:
      - Attempts Gemini first
      - Falls back to local model on any failure
    """

    LOCAL_MODEL_NAME = "all-MiniLM-L6-v2"
    GEMINI_EMBED_MODEL = "text-embedding-004"
    GEMINI_GENERATE_MODEL = "gemini-1.5-flash"
    DEFAULT_TOP_N = 5
    DEFAULT_THRESHOLD = 0.30

    def __init__(self, controls_path: Optional[str] = None):
        # State
        self._controls: list[dict] = []
        self._control_texts: list[str] = []
        self._is_ready = False

        # Gemini engine
        self._gemini_client = None
        self._gemini_available = False
        self._gemini_control_embeddings: Optional[np.ndarray] = None

        # Local NLP engine
        self._local_model = None
        self._local_control_embeddings: Optional[np.ndarray] = None

        # Resolve controls JSON path (prefer enriched dataset if available)
        if controls_path:
            self._controls_path = Path(controls_path)
        else:
            enriched_path = (
                Path(__file__).resolve().parents[2]
                / "data" / "iso27001-controls-enriched.json"
            )
            standard_path = (
                Path(__file__).resolve().parents[2]
                / "data" / "iso27001-controls.json"
            )
            self._controls_path = enriched_path if enriched_path.exists() else standard_path

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load models and pre-compute control embeddings. Call once at startup."""
        logger.info(f"AI Service: Loading ISO 27001 controls from {self._controls_path.name}...")
        try:
            self._load_controls()
        except Exception as e:
            logger.error(f"AI Service: Failed to load controls ({e})")
            return

        # --- Try Gemini first (Lightweight) ---
        self._init_gemini()

        # --- Load local model for embeddings ---
        # Note: Even if Gemini is available for generation, we still use local embeddings
        # for semantic matching and gap analysis tasks.
        self._init_local_model()

        if self._gemini_available or self._local_model is not None:
            self._is_ready = True
            engines = []
            if self._gemini_available: engines.append("Gemini (Generation)")
            if self._local_model: engines.append("Local NLP (Embeddings + BM25)")
            logger.info(f"AI Service: Ready ✓  Engines: {', '.join(engines)}")
        else:
            logger.error("AI Service: Initialization failed. No AI engines available.")

    def _load_controls(self) -> None:
        """Load and parse the ISO 27001 controls JSON with rich domain representations."""
        if not self._controls_path.exists():
            raise FileNotFoundError(f"Controls file not found: {self._controls_path}")

        with open(self._controls_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._controls = data.get("controls", [])
        self._control_texts = []
        for c in self._controls:
            annex = c.get("annex") or c.get("id", "")
            title = c.get("title", "")
            desc = c.get("description", "")
            extra = c.get("text", "")
            synonyms = ISO_DOMAIN_SYNONYMS.get(annex, "")
            # Rich semantic representation with explicit Annex identifier, title, description, and domain keywords
            rep = f"Control {annex}: {title}. {desc} {extra} {synonyms}".strip()
            self._control_texts.append(rep)

    def _init_gemini(self) -> None:
        """Try to initialize the Gemini client for text generation."""
        api_key = (settings.GEMINI_API_KEY or "").strip()
        if not api_key:
            logger.info("AI Service: No GEMINI_API_KEY found. Gemini generation disabled.")
            return

        try:
            self._gemini_client = genai.Client(api_key=api_key)
            self._gemini_available = True
            logger.info("AI Service: Gemini generation client initialized ✓")

        except Exception as e:
            logger.warning(f"AI Service: Gemini init failed ({e}). Generator disabled.")
            self._gemini_available = False

    def _init_local_model(self) -> None:
        """Load the local SentenceTransformer model and pre-embed controls."""
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"AI Service: Loading local model '{self.LOCAL_MODEL_NAME}'...")
            self._local_model = SentenceTransformer(self.LOCAL_MODEL_NAME)

            logger.info(f"AI Service: Computing local embeddings for {len(self._controls)} controls...")
            self._local_control_embeddings = self._local_model.encode(
                self._control_texts, convert_to_numpy=True, show_progress_bar=False
            )

            # Initialize BM25 sparse index over rich control definitions
            try:
                from rank_bm25 import BM25Okapi
                tokenized_corpus = [t.lower().split() for t in self._control_texts]
                self._bm25_model = BM25Okapi(tokenized_corpus)
                logger.info("AI Service: Initialized BM25 sparse control index ✓")
            except Exception as bm25_err:
                logger.warning(f"AI Service: BM25 init failed ({bm25_err}); continuing with dense-only")
                self._bm25_model = None

            logger.info("AI Service: Local NLP model loaded ✓")

        except Exception as e:
            logger.error(f"AI Service: Local model failed to load ({e})")
            if not self._gemini_available:
                raise RuntimeError(
                    "AI Service: Neither Gemini nor local model available. Cannot start."
                )

    async def sync_vector_store(self) -> None:
        """
        Async hook: Initializes Qdrant collections and populates grc_iso_controls.
        Call during startup after initialize().
        """
        from app.services.vector_store import vector_store
        try:
            success = await vector_store.initialize_collections()
            if success and self._controls and self._local_control_embeddings is not None:
                await vector_store.upsert_iso_controls(self._controls, self._local_control_embeddings)
                logger.info("AI Service: Synced ISO control embeddings to Qdrant ✓")
        except Exception as e:
            logger.warning(f"AI Service: Qdrant sync skipped ({e})")

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @property
    def active_engine(self) -> str:
        return "hybrid" if self._gemini_available else "local"

    # ------------------------------------------------------------------
    # Embedding helper
    # ------------------------------------------------------------------

    def _embed_text(self, text: str) -> np.ndarray:
        """Embed text using local NLP model."""
        if self._local_model is not None:
            return self._local_model.encode([text], convert_to_numpy=True)
        raise RuntimeError("Local NLP engine not available.")

    def _embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts using local NLP model."""
        if self._local_model is not None:
            return self._local_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        raise RuntimeError("Local NLP engine not available.")

    def _get_control_embeddings(self) -> np.ndarray:
        """Get the pre-computed local control embeddings."""
        if self._local_control_embeddings is not None:
            return self._local_control_embeddings
        raise RuntimeError("No control embeddings available.")

    # ------------------------------------------------------------------
    # Evidence Analysis
    # ------------------------------------------------------------------

    def analyze_evidence(
        self,
        text: str,
        top_n: int = DEFAULT_TOP_N,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> EvidenceAnalysisResult:
        """
        Analyze evidence text and return matched ISO 27001 controls using hybrid BM25 + dense matching.

        Args:
            text: The extracted text content of the evidence document.
            top_n: Maximum number of control matches to return.
            threshold: Minimum cosine similarity score (0.0 – 1.0).

        Returns:
            EvidenceAnalysisResult with category, matched controls, and summary.
        """
        if not self._is_ready:
            raise RuntimeError("AI Service not initialized. Call initialize() first.")

        # 1. Categorize the evidence
        category = self._categorize(text)

        # 2. Compute similarity against all controls (Hybrid Dense + BM25)
        text_embedding = self._embed_text(text)
        control_embeddings = self._get_control_embeddings()
        dense_scores = cosine_similarity(text_embedding, control_embeddings)[0]

        if getattr(self, "_bm25_model", None) is not None:
            tokens = text.lower().split()
            bm25_scores = np.array(self._bm25_model.get_scores(tokens))
            bm25_max = bm25_scores.max()
            bm25_norm = (bm25_scores / bm25_max) if bm25_max > 0 else np.zeros_like(bm25_scores)
            dense_norm = np.clip((dense_scores + 1) / 2.0, 0, 1)
            # Weighted hybrid score: 0.65 dense semantic + 0.35 sparse keyword
            hybrid_scores = (0.65 * dense_norm) + (0.35 * bm25_norm)
            ranked_indices = np.argsort(hybrid_scores)[::-1]
        else:
            ranked_indices = np.argsort(dense_scores)[::-1]

        # 3. Rank and filter
        matched_controls: list[ControlMatch] = []

        for idx in ranked_indices:
            score = float(dense_scores[idx])
            if score < threshold:
                break
            if len(matched_controls) >= top_n:
                break

            control = self._controls[idx]
            matched_controls.append(ControlMatch(
                control_id=control["id"],
                annex=control.get("annex", control["id"]),
                title=control["title"],
                description=control["description"],
                clause_id=control.get("clauseId", control["id"]),
                confidence=score,
            ))

        # 4. Generate summary
        if matched_controls:
            top_control = matched_controls[0]
            summary = (
                f"This evidence is categorized as '{category}' and most closely "
                f"relates to control {top_control.annex} ({top_control.title}) "
                f"with {top_control.confidence}% confidence."
            )
        else:
            summary = (
                f"This evidence is categorized as '{category}' but no strong "
                f"control matches were found above the {threshold * 100}% threshold."
            )

        return EvidenceAnalysisResult(
            category=category,
            matched_controls=matched_controls,
            summary=summary,
        )

    def analyze_evidence_pdf(
        self,
        file_bytes: bytes,
        top_n: int = DEFAULT_TOP_N,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> EvidenceAnalysisResult:
        """
        Extract text from a PDF file and analyze it.

        Args:
            file_bytes: Raw bytes of the uploaded PDF.
            top_n: Maximum number of control matches to return.
            threshold: Minimum cosine similarity score.

        Returns:
            EvidenceAnalysisResult
        """
        text = extract_text_from_pdf(file_bytes)
        if not text.strip():
            raise ValueError("Could not extract any text from the uploaded PDF.")
        return self.analyze_evidence(text, top_n=top_n, threshold=threshold)

    async def analyze_evidence_qdrant(
        self,
        text: str,
        top_n: int = DEFAULT_TOP_N,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> EvidenceAnalysisResult:
        """
        Qdrant-backed evidence analysis: embeds the text locally, queries the
        ``grc_iso_controls`` collection for the nearest control vectors, and
        returns an EvidenceAnalysisResult.

        Preferred over the synchronous ``analyze_evidence()`` method because:
        - All retrieval goes through Qdrant (single source of truth).
        - In-memory cosine_similarity is not needed at inference time.
        - Falls back gracefully to the in-memory path if Qdrant is offline.

        Args:
            text: Extracted text of the evidence document.
            top_n: Maximum number of control matches to return.
            threshold: Minimum cosine similarity score (0.0 – 1.0).

        Returns:
            EvidenceAnalysisResult with category, matched controls, and summary.
        """
        if not self._is_ready:
            raise RuntimeError("AI Service not initialized. Call initialize() first.")

        # 1. Categorize the evidence
        category = self._categorize(text)

        from app.services.vector_store import vector_store

        # 2a. Qdrant path (preferred) ─────────────────────────────────────────
        if vector_store.is_ready:
            text_embedding = self._embed_text(text)
            hits = await vector_store.dense_search(
                query_vector=text_embedding,
                collection_name=settings.QDRANT_COLLECTION_ISO_CONTROLS,
                top_k=min(top_n * 4, len(self._controls)),  # over-fetch; filter by threshold below
            )

            matched_controls: list[ControlMatch] = []
            for hit in hits:
                score = float(hit.get("score", 0.0))
                if score < threshold:
                    break
                if len(matched_controls) >= top_n:
                    break
                payload = hit.get("payload", {})
                matched_controls.append(ControlMatch(
                    control_id=payload.get("control_id", ""),
                    annex=payload.get("annex", ""),
                    title=payload.get("title", ""),
                    description=payload.get("description", ""),
                    clause_id=payload.get("clause_id", ""),
                    confidence=score,
                ))

            logger.debug(
                f"AI Service (Qdrant path): {len(matched_controls)} control matches "
                f"above threshold={threshold} for text len={len(text)}"
            )

        # 2b. Qdrant Unreachable -> Fail-Closed ───────────────────────────────
        else:
            raise RuntimeError(
                "Qdrant vector store is offline/unreachable. Evidence analysis cannot proceed in degraded mode."
            )

        # 3. Generate summary
        if matched_controls:
            top_control = matched_controls[0]
            summary = (
                f"This evidence is categorized as '{category}' and most closely "
                f"relates to control {top_control.annex} ({top_control.title}) "
                f"with {top_control.confidence}% confidence."
            )
        else:
            summary = (
                f"This evidence is categorized as '{category}' but no strong "
                f"control matches were found above the {threshold * 100}% threshold."
            )

        return EvidenceAnalysisResult(
            category=category,
            matched_controls=matched_controls,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Full Document Analysis (Step 3 Engine)
    # ------------------------------------------------------------------

    def analyze_document(self, text: str) -> DocumentAnalysisAIResult:
        """
        Comprehensive document analysis for Step 3.
        Detects practices, maps controls, and identifies domain-specific gaps.
        """
        if not self._is_ready:
            raise RuntimeError("AI Service not initialized.")

        # Try Gemini, fallback to local
        if self._gemini_available and self._gemini_client:
            try:
                return self._analyze_document_gemini(text)
            except Exception as e:
                logger.warning(f"Gemini document analysis failed: {e}")

        return self._analyze_document_local(text)

    def _analyze_document_gemini(self, text: str) -> DocumentAnalysisAIResult:
        """Deep analysis using Gemini generative model."""
        prompt = f"""You are an ISO 27001 Auditor. Analyze the following security document text and extract structured compliance data.

Document Text:
{text[:8000]}  # Limit text for prompt constraints

Return ONLY a valid JSON object with these exact fields:
{{
  "summary": "<one sentence overview>",
  "category": "<policy|procedure|architecture|standard>",
  "security_practices": [
    {{"practice": "...", "excerpt": "...", "strength": "strong|partial"}}
  ],
  "implemented_controls": [
    {{"annex": "5.1", "title": "Policies for information security", "confidence": 0.95, "reason": "..."}}
  ],
  "missing_controls": [
    {{"annex": "8.12", "title": "Data leakage prevention", "reason": "Found mention of data but no DLP rules."}}
  ]
}}

Guidelines:
- Categorize the document accurately.
- Identify 3-10 implemented controls from ISO 27001:2022.
- Identify 1-3 missing controls that logically SHOULD be in this type of document.
- Extract specific practices found in the text."""

        response = self._gemini_client.models.generate_content(
            model=self.GEMINI_GENERATE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        result = json.loads(raw_text)
        
        return DocumentAnalysisAIResult(
            summary=result.get("summary", "Analysis completed."),
            category=result.get("category", "general"),
            implemented_controls=result.get("implemented_controls", []),
            missing_controls=result.get("missing_controls", []),
            security_practices=result.get("security_practices", [])
        )

    def _analyze_document_local(self, text: str) -> DocumentAnalysisAIResult:
        """Heuristic analysis using local embeddings and keywords."""
        # Categorize
        category = self._categorize(text)
        
        # Simple similarity for implemented controls
        # TODO: PROD-BUG — Silent degraded fallback (same issue as llm_backend.py:70).
        # analyze_evidence() runs entirely in-memory with no Qdrant involvement.
        # Called here as a local heuristic fallback from _analyze_document_local, so
        # any caller receiving a DocumentAnalysisAIResult from this path has no way to
        # distinguish it from a Qdrant-backed result. Needs a 'retrieval_mode' flag.
        # Tracked: do not fix here — out of scope for calibration work.
        basic_res = self.analyze_evidence(text, top_n=5)
        implemented = [
            {"annex": m.annex, "title": m.title, "confidence": m.confidence/100, "reason": "Semantic similarity match."}
            for m in basic_res.matched_controls
        ]
        
        # Basic practice detection via keywords
        practices = []
        text_lower = text.lower()
        if "mfa" in text_lower or "multi-factor" in text_lower:
            practices.append({"practice": "Multi-factor authentication", "strength": "strong"})
        if "encryption" in text_lower or "aes-256" in text_lower:
            practices.append({"practice": "Data encryption", "strength": "strong"})
        if "review" in text_lower or "audit" in text_lower:
            practices.append({"practice": "Periodic review compliance", "strength": "partial"})

        return DocumentAnalysisAIResult(
            summary=basic_res.summary,
            category=category,
            implemented_controls=implemented,
            missing_controls=[], # Local fallback is poor at detecting missing logic
            security_practices=practices
        )

    def _categorize(self, text: str) -> str:
        """Classify evidence into a category based on keyword matching.

        Tie-breaking is deterministic: highest keyword count wins; ties broken
        alphabetically by category name so output is stable across runs.
        """
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if scores:
            # Sort by (-score, name) so highest score wins; ties break on name (deterministic)
            return min(scores, key=lambda k: (-scores[k], k))
        return "general"


    # ------------------------------------------------------------------
    # Risk Suggestion
    # ------------------------------------------------------------------

    async def suggest_risk_score(self, description: str) -> RiskSuggestion:
        """
        Analyze a risk description and suggest likelihood/impact scores.

        Primary: Uses Gemini generative model with structured output.
        Fallback: Heuristic based on Qdrant dense vector search.
        """
        if not self._is_ready:
            raise RuntimeError("AI Service not initialized. Call initialize() first.")

        # --- Try Gemini generative model ---
        if self._gemini_available and self._gemini_client:
            try:
                return self._suggest_risk_gemini(description)
            except Exception as e:
                logger.warning(f"Gemini risk suggestion failed ({e}). Falling back to local.")

        # --- Fallback to local heuristic ---
        return await self._suggest_risk_local(description)

    def _suggest_risk_gemini(self, description: str) -> RiskSuggestion:
        """Use Gemini to generate a risk score with structured reasoning."""
        # Build a context of all control names for the model
        control_list = "\n".join(
            f"- {c['annex']}: {c['title']}" for c in self._controls[:30]
        )

        prompt = f"""You are an ISO 27001 risk assessment expert. Analyze the following risk description and provide a structured risk assessment.

Risk Description:
{description}

Available ISO 27001 Controls (partial list):
{control_list}

Respond with ONLY a valid JSON object with these exact fields:
{{
  "likelihood": <integer 1-5>,
  "impact": <integer 1-5>,
  "risk_score": <integer = likelihood * impact>,
  "reasoning": "<brief explanation of the risk assessment>",
  "related_controls": ["<annex_id> <control_title>", ...]
}}

Guidelines:
- likelihood: 1=Rare, 2=Unlikely, 3=Possible, 4=Likely, 5=Almost Certain
- impact: 1=Insignificant, 2=Minor, 3=Moderate, 4=Major, 5=Catastrophic
- related_controls: List 1-5 ISO 27001 controls that can help mitigate this risk
- reasoning: Explain why you chose these scores in 1-2 sentences"""

        response = self._gemini_client.models.generate_content(
            model=self.GEMINI_GENERATE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )

        # Parse the JSON from Gemini's response
        response_text = response.text.strip()

        # Strip markdown code fences if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            response_text = "\n".join(lines)

        result = json.loads(response_text)

        likelihood = max(1, min(5, int(result.get("likelihood", 3))))
        impact = max(1, min(5, int(result.get("impact", 3))))

        return RiskSuggestion(
            likelihood=likelihood,
            impact=impact,
            risk_score=likelihood * impact,
            reasoning=result.get("reasoning", "AI-generated assessment."),
            related_controls=result.get("related_controls", []),
        )

    async def _suggest_risk_local(self, description: str) -> RiskSuggestion:
        """Fallback: heuristic risk scoring using Qdrant dense vector search."""
        from app.services.vector_store import vector_store
        if not vector_store.is_ready:
            raise RuntimeError(
                "Qdrant vector store is offline/unreachable. Risk suggestion cannot proceed in degraded mode."
            )

        text_embedding = self._embed_text(description)
        hits = await vector_store.dense_search(
            query_vector=text_embedding,
            collection_name=settings.QDRANT_COLLECTION_ISO_CONTROLS,
            top_k=5,
        )

        related_controls: list[str] = []
        relevance_scores: list[float] = []

        for hit in hits:
            score = float(hit.get("score", 0.0))
            if score < 0.25:
                break
            payload = hit.get("payload", {})
            related_controls.append(f"{payload.get('annex', '')} {payload.get('title', '')}")
            relevance_scores.append(score)

        # Heuristic scoring
        avg_relevance = np.mean(relevance_scores) if relevance_scores else 0.0
        num_controls = len(related_controls)

        if avg_relevance > 0.6 and num_controls >= 3:
            likelihood, impact = 4, 4
            reasoning = "High semantic overlap with multiple controls suggests a broad, well-known risk."
        elif avg_relevance > 0.4:
            likelihood, impact = 3, 3
            reasoning = "Moderate overlap with controls suggests a recognized risk area."
        elif avg_relevance > 0.25:
            likelihood, impact = 2, 3
            reasoning = "Some control relevance detected; risk may be partially addressed."
        else:
            likelihood, impact = 2, 2
            reasoning = "Low control mapping; this may be an emerging or novel risk."

        return RiskSuggestion(
            likelihood=likelihood,
            impact=impact,
            risk_score=likelihood * impact,
            reasoning=reasoning,
            related_controls=related_controls,
        )

    # ------------------------------------------------------------------
    # Compliance Gap Analysis
    # ------------------------------------------------------------------

    async def get_compliance_gaps(
        self, evidence_texts: list[str], threshold: float = 0.40
    ) -> list[dict]:
        """
        Given all evidence texts in the system, identify which controls
        have NO matching evidence (compliance gaps). Uses Qdrant's
        grc_iso_controls collection as the source of truth.
        """
        if not self._is_ready:
            raise RuntimeError("AI Service not initialized. Call initialize() first.")

        if not evidence_texts:
            return [
                {"control_id": c["id"], "annex": c["annex"], "title": c["title"]}
                for c in self._controls
            ]

        from app.services.vector_store import vector_store
        if not vector_store.is_ready:
            initialized = await vector_store.initialize_collections()
            if initialized:
                control_embeddings = self._embed_texts(self._control_texts)
                await vector_store.upsert_iso_controls(self._controls, control_embeddings)
            else:
                raise RuntimeError("Qdrant vector store is not ready for compliance gap analysis.")

        control_best_scores: dict[str, float] = {c["id"]: 0.0 for c in self._controls}
        for evidence_text in evidence_texts:
            evidence_embedding = self._embed_text(evidence_text)
            hits = await vector_store.dense_search(
                query_vector=evidence_embedding,
                collection_name=settings.QDRANT_COLLECTION_ISO_CONTROLS,
                top_k=len(self._controls),
            )
            for hit in hits:
                payload = hit.get("payload", {})
                control_id = payload.get("control_id")
                if control_id in control_best_scores:
                    control_best_scores[control_id] = max(
                        control_best_scores[control_id],
                        float(hit.get("score", 0.0)),
                    )

        gaps = []
        for control in self._controls:
            max_sim = control_best_scores.get(control["id"], 0.0)
            if max_sim < threshold:
                gaps.append({
                    "control_id": control["id"],
                    "annex": control["annex"],
                    "title": control["title"],
                    "best_match_score": round(max_sim * 100, 1),
                })

        return gaps

    def map_policy_chunks_to_controls(
        self,
        chunks: list,
        embeddings: Optional[np.ndarray] = None,
        threshold: Optional[float] = None,
    ) -> list[dict]:
        """
        Map policy document chunks to ISO 27001 controls using multi-chunk aggregation.
        Each control mapping contains all contributing chunks exceeding threshold.
        Default threshold: settings.POLICY_MATCH_THRESHOLD (0.40).
        """
        if not self._is_ready:
            self.initialize()

        thresh = threshold if threshold is not None else settings.POLICY_MATCH_THRESHOLD
        if not chunks:
            return []

        if embeddings is None or len(embeddings) != len(chunks):
            chunk_texts = [c.text for c in chunks]
            embeddings = self._embed_texts(chunk_texts)

        # Control embeddings
        ctrl_embeddings = self._get_control_embeddings()

        # Compute cosine similarity matrix: (num_chunks, num_controls)
        sim_matrix = cosine_similarity(embeddings, ctrl_embeddings)

        # Group by control annex
        control_groups: dict[str, dict] = {}
        for c_idx, chunk in enumerate(chunks):
            for ctrl_idx, ctrl in enumerate(self._controls):
                score = float(sim_matrix[c_idx, ctrl_idx])
                if score >= thresh:
                    annex = ctrl["annex"]
                    if annex not in control_groups:
                        control_groups[annex] = {
                            "control_annex": annex,
                            "title": ctrl["title"],
                            "clause_id": ctrl.get("clauseId", annex),
                            "mapping_status": "suggested",
                            "confirmed_by": None,
                            "confirmed_at": None,
                            "policy_chunks": [],
                        }
                    control_groups[annex]["policy_chunks"].append({
                        "chunk_id": getattr(chunk, "chunk_id", str(c_idx)),
                        "section_heading": getattr(chunk, "section_heading", "General"),
                        "page_number": getattr(chunk, "page_number", 1),
                        "excerpt": chunk.text[:300],
                        "confidence": round(score * 100, 1),
                    })

        mappings = []
        for annex, data in control_groups.items():
            # Sort contributing chunks by confidence descending
            data["policy_chunks"].sort(key=lambda x: -x["confidence"])
            data["composite_confidence"] = data["policy_chunks"][0]["confidence"] if data["policy_chunks"] else 0.0
            mappings.append(data)

        # Sort mapped controls by composite confidence descending
        mappings.sort(key=lambda x: -x["composite_confidence"])
        return mappings

    def evaluate_policy_evidence_alignment(
        self,
        policy_text: Union[str, list[str]],
        evidence_text: str,
        control_title: str = "",
        control_annex: str = "",
    ) -> dict:
        """
        Evaluate whether the provided evidence aligns with the company's specific internal policy.
        Incorporates citation-verified vagueness detection ("policy_too_vague").
        
        Returns:
            dict containing:
            - is_aligned: bool
            - compliance_state: str ("satisfied" | "policy_evidence_mismatch" | "policy_too_vague")
            - confidence: float (0.0 to 100.0)
            - mismatch_reason: Optional[str]
            - cited_excerpt: Optional[str]
            - similarity: float
        """
        if not self._is_ready:
            self.initialize()

        if isinstance(policy_text, list):
            combined_policy_text = "\n\n".join(policy_text).strip()
        else:
            combined_policy_text = policy_text.strip()

        if not combined_policy_text or not evidence_text.strip():
            return {
                "is_aligned": False,
                "compliance_state": "policy_evidence_mismatch",
                "confidence": 0.0,
                "mismatch_reason": "Missing policy or evidence text for comparison",
                "cited_excerpt": None,
                "similarity": 0.0,
            }

        p_lower = combined_policy_text.lower()
        e_lower = evidence_text.lower()

        # ------------------------------------------------------------------
        # 1. Citation-Verified Vagueness Detection ("policy_too_vague")
        # ------------------------------------------------------------------
        vague_phrases = [
            "appropriate measures",
            "reasonable measures",
            "reasonable steps",
            "reasonable efforts",
            "as deemed necessary",
            "when feasible",
            "industry standard tools",
            "ensure good security",
            "take proper precautions",
            "maintain adequate safeguards",
            "standard security practices",
        ]

        has_concrete_criteria = any([
            bool(re.search(r'\d+', p_lower)),  # Numeric bounds (e.g. 14, 90, 256, 30)
            "mfa" in p_lower or "2fa" in p_lower or "multi-factor" in p_lower,
            "aes" in p_lower or "rsa" in p_lower or "tls" in p_lower or "sha" in p_lower,
            "daily" in p_lower or "weekly" in p_lower or "monthly" in p_lower or "quarterly" in p_lower or "annual" in p_lower,
            "role-based" in p_lower or "rbac" in p_lower or "least privilege" in p_lower,
        ])

        found_vague_phrases = [phrase for phrase in vague_phrases if phrase in p_lower]
        if found_vague_phrases and not has_concrete_criteria:
            # Policy relies solely on vague, non-auditable statements
            vague_citation = next((p for p in combined_policy_text.splitlines() if any(v in p.lower() for v in found_vague_phrases)), combined_policy_text[:200])
            return {
                "is_aligned": False,
                "compliance_state": "policy_too_vague",
                "confidence": 85.0,
                "mismatch_reason": f"Internal policy uses subjective, non-auditable language ({', '.join(found_vague_phrases)}) without defining verifiable operational thresholds.",
                "cited_excerpt": vague_citation.strip(),
                "similarity": 0.0,
            }

        # ------------------------------------------------------------------
        # 2. Dense Semantic Similarity
        # ------------------------------------------------------------------
        p_emb = self._embed_text(combined_policy_text)
        e_emb = self._embed_text(evidence_text)
        sim = float(cosine_similarity(p_emb.reshape(1, -1), e_emb.reshape(1, -1))[0][0])
        sim_pct = round(max(0.0, min(1.0, sim)) * 100, 1)

        # ------------------------------------------------------------------
        # 3. Rule & Constraint Contradiction Checks ("policy_evidence_mismatch")
        # ------------------------------------------------------------------
        mismatch_reasons = []

        # Example: Password length mismatch check
        p_lengths = re.findall(r'(?:min(?:imum)?\s+(?:password\s+)?length(?:\s+of)?|at\s+least|minimum\s+of)\s*[:=]?\s*(\d+)', p_lower)
        e_lengths = re.findall(r'(?:min(?:imum)?\s+(?:password\s+)?length(?:\s+of)?|min_len(?:gth)?|password_length)\s*[:=]?\s*(\d+)', e_lower)
        if p_lengths and e_lengths:
            req_len = int(p_lengths[0])
            actual_len = int(e_lengths[0])
            if actual_len < req_len:
                mismatch_reasons.append(
                    f"Policy mandates minimum password length of {req_len} characters, but evidence config shows {actual_len} characters."
                )

        # Example: MFA required vs disabled
        if ("mfa required" in p_lower or "multi-factor authentication mandatory" in p_lower or "mfa: enabled" in p_lower or "mfa mandatory" in p_lower) and \
           ("mfa: disabled" in e_lower or "mfa_enabled = false" in e_lower or "mfa: false" in e_lower or "2fa disabled" in e_lower or "mfa disabled" in e_lower):
            mismatch_reasons.append(
                "Policy mandates multi-factor authentication, but evidence config indicates MFA is disabled/false."
            )

        # Example: Rotation interval mismatch
        p_rot = re.findall(r'(\d+)[-\s]day\s+rotation', p_lower)
        e_rot = re.findall(r'(\d+)[-\s]day\s+rotation', e_lower)
        if p_rot and e_rot:
            req_rot = int(p_rot[0])
            actual_rot = int(e_rot[0])
            if actual_rot > req_rot:
                mismatch_reasons.append(
                    f"Policy mandates rotation every {req_rot} days, but evidence shows {actual_rot} days."
                )

        if mismatch_reasons:
            return {
                "is_aligned": False,
                "compliance_state": "policy_evidence_mismatch",
                "confidence": sim_pct,
                "mismatch_reason": "; ".join(mismatch_reasons),
                "cited_excerpt": None,
                "similarity": sim,
            }

        # ------------------------------------------------------------------
        # 4. Satisfaction Evaluation
        # ------------------------------------------------------------------
        if sim >= 0.35:
            return {
                "is_aligned": True,
                "compliance_state": "satisfied",
                "confidence": sim_pct,
                "mismatch_reason": None,
                "cited_excerpt": None,
                "similarity": sim,
            }
        else:
            return {
                "is_aligned": False,
                "compliance_state": "policy_evidence_mismatch",
                "confidence": sim_pct,
                "mismatch_reason": f"Evidence content has low semantic overlap ({sim_pct}%) with specific internal policy requirements.",
                "cited_excerpt": None,
                "similarity": sim,
            }


async def _run_document_analysis_async(text: str) -> dict:
    """Async Qdrant-backed document analysis pipeline.

    This is the canonical entry point for the ingestion pipeline and all API
    routes. It uses Qdrant as the primary source of truth for control
    similarity and falls back to the in-memory path when Qdrant is offline.

    Returns a dict with the same schema as the legacy ``_run_document_analysis``.
    """
    if not ai_service.is_ready:
        ai_service.initialize()

    category = ai_service._categorize(text)
    evidence_result = await ai_service.analyze_evidence_qdrant(
        text, top_n=93, threshold=0.30
    )

    implemented = []
    weak_matches = []

    for match in evidence_result.matched_controls:
        item = {
            "control_annex": match.annex,
            "title": match.title,
            "confidence": match.confidence,
            "clause_id": match.clause_id,
        }
        if match.confidence >= 50:
            implemented.append(item)
        elif match.confidence >= 30:
            weak_matches.append(item)

    # Sort for deterministic output — confidence descending, annex ascending on ties
    implemented.sort(key=lambda x: (-x["confidence"], x["control_annex"]))
    weak_matches.sort(key=lambda x: (-x["confidence"], x["control_annex"]))

    matched_annexes = {m.annex for m in evidence_result.matched_controls}
    missing = []
    for ctrl in ai_service._controls:
        if ctrl["annex"] not in matched_annexes:
            missing.append({
                "control_annex": ctrl["annex"],
                "title": ctrl["title"],
                "reason": "No reference found in document",
            })

    practices = _extract_security_practices(text)

    return {
        "document_category": category,
        "summary": evidence_result.summary,
        "implemented_controls": implemented,
        "weak_matches": weak_matches,
        "missing_controls": missing,
        "security_practices": practices,
        "total_controls_checked": len(ai_service._controls),
        "strong_matches": len(implemented),
        "weak_match_count": len(weak_matches),
        "missing_count": len(missing),
    }



def _extract_security_practices(text: str) -> list[dict]:
    """Extract security practices by scanning for key phrases."""
    text_lower = text.lower()
    
    practice_patterns = {
        "Multi-factor authentication": (["mfa", "multi-factor", "two-factor", "2fa"], ["5.17", "8.5"]),
        "Access control policy": (["access control", "role-based access", "rbac", "least privilege"], ["5.15", "5.18", "8.2"]),
        "Data encryption": (["encryption", "encrypted", "aes", "tls", "ssl", "cryptograph"], ["8.24"]),
        "Security awareness training": (["security training", "awareness program", "security awareness"], ["6.3"]),
        "Incident response": (["incident response", "incident management", "security incident"], ["5.24", "5.25", "5.26"]),
        "Backup procedures": (["backup", "data backup", "recovery point"], ["8.13"]),
        "Change management": (["change management", "change control", "change request"], ["8.32"]),
        "Vulnerability management": (["vulnerability scan", "penetration test", "vulnerability management"], ["8.8"]),
        "Network security": (["firewall", "network segmentation", "intrusion detection", "ids", "ips"], ["8.20", "8.21", "8.22"]),
        "Logging and monitoring": (["audit log", "event log", "monitoring", "siem"], ["8.15", "8.16"]),
        "Password policy": (["password policy", "password complexity", "password rotation"], ["5.17"]),
        "Data classification": (["data classification", "information classification", "labeling"], ["5.12", "5.13"]),
        "Business continuity": (["business continuity", "disaster recovery", "bcp", "drp"], ["5.29", "5.30"]),
        "Secure development": (["secure development", "sdlc", "secure coding", "code review"], ["8.25", "8.28"]),
        "Supplier management": (["vendor management", "supplier assessment", "third-party"], ["5.19", "5.20", "5.21"]),
    }
    
    found_practices = []
    for practice_name, (keywords, related_controls) in practice_patterns.items():
        if any(kw in text_lower for kw in keywords):
            found_practices.append({
                "practice": practice_name,
                "related_controls": related_controls,
            })
    
    return found_practices


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

ai_service = AIService()

