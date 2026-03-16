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
from io import BytesIO
from pathlib import Path
from typing import Optional

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
    """Extract text content from a PDF file's bytes."""
    from PyPDF2 import PdfReader

    reader = PdfReader(BytesIO(file_bytes))
    pages_text: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text.strip())

    return "\n\n".join(pages_text)


# ---------------------------------------------------------------------------
# Core AI Service — Hybrid Engine
# ---------------------------------------------------------------------------

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

        # Resolve controls JSON path
        if controls_path:
            self._controls_path = Path(controls_path)
        else:
            self._controls_path = (
                Path(__file__).resolve().parents[2]  # backend/ (or /app/ in Docker)
                / "data" / "iso27001-controls.json"
            )

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load models and pre-compute control embeddings. Call once at startup."""
        logger.info("AI Service: Loading ISO 27001 controls...")
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
            if self._local_model: engines.append("Local NLP (Embeddings)")
            logger.info(f"AI Service: Ready ✓  Engines: {', '.join(engines)}")
        else:
            logger.error("AI Service: Initialization failed. No AI engines available.")

    def _load_controls(self) -> None:
        """Load and parse the ISO 27001 controls JSON."""
        if not self._controls_path.exists():
            raise FileNotFoundError(f"Controls file not found: {self._controls_path}")

        with open(self._controls_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._controls = data.get("controls", [])
        self._control_texts = [
            f"{c['title']}. {c['description']}" for c in self._controls
        ]

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
            logger.info("AI Service: Local NLP model loaded ✓")

        except Exception as e:
            logger.error(f"AI Service: Local model failed to load ({e})")
            if not self._gemini_available:
                raise RuntimeError(
                    "AI Service: Neither Gemini nor local model available. Cannot start."
                )

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
        Analyze evidence text and return matched ISO 27001 controls.

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

        # 2. Compute similarity against all controls
        text_embedding = self._embed_text(text)
        control_embeddings = self._get_control_embeddings()
        similarities = cosine_similarity(text_embedding, control_embeddings)[0]

        # 3. Rank and filter
        ranked_indices = np.argsort(similarities)[::-1]
        matched_controls: list[ControlMatch] = []

        for idx in ranked_indices:
            score = float(similarities[idx])
            if score < threshold:
                break
            if len(matched_controls) >= top_n:
                break

            control = self._controls[idx]
            matched_controls.append(ControlMatch(
                control_id=control["id"],
                annex=control["annex"],
                title=control["title"],
                description=control["description"],
                clause_id=control["clauseId"],
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
        """Classify evidence into a category based on keyword matching."""
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if scores:
            return str(max(scores, key=lambda k: scores[k]))
        return "general"

    # ------------------------------------------------------------------
    # Risk Suggestion
    # ------------------------------------------------------------------

    def suggest_risk_score(self, description: str) -> RiskSuggestion:
        """
        Analyze a risk description and suggest likelihood/impact scores.

        Primary: Uses Gemini generative model with structured output.
        Fallback: Heuristic based on local embedding similarity.
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
        return self._suggest_risk_local(description)

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

    def _suggest_risk_local(self, description: str) -> RiskSuggestion:
        """Fallback: heuristic risk scoring using local embeddings."""
        text_embedding = self._embed_text(description)
        control_embeddings = self._get_control_embeddings()
        similarities = cosine_similarity(text_embedding, control_embeddings)[0]
        ranked_indices = np.argsort(similarities)[::-1]

        related_controls: list[str] = []
        relevance_scores: list[float] = []

        for idx in ranked_indices[:5]:
            score = float(similarities[idx])
            if score < 0.25:
                break
            control = self._controls[idx]
            related_controls.append(f"{control['annex']} {control['title']}")
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

    def get_compliance_gaps(
        self, evidence_texts: list[str], threshold: float = 0.40
    ) -> list[dict]:
        """
        Given all evidence texts in the system, identify which controls
        have NO matching evidence (compliance gaps).
        """
        if not self._is_ready:
            raise RuntimeError("AI Service not initialized. Call initialize() first.")

        if not evidence_texts:
            return [
                {"control_id": c["id"], "annex": c["annex"], "title": c["title"]}
                for c in self._controls
            ]

        # Encode all evidence
        evidence_embeddings = self._embed_texts(evidence_texts)
        control_embeddings = self._get_control_embeddings()

        # For each control, check if ANY evidence matches above threshold
        gaps = []
        for idx, control in enumerate(self._controls):
            control_emb = control_embeddings[idx].reshape(1, -1)
            sims = cosine_similarity(control_emb, evidence_embeddings)[0]
            max_sim = float(np.max(sims))

            if max_sim < threshold:
                gaps.append({
                    "control_id": control["id"],
                    "annex": control["annex"],
                    "title": control["title"],
                    "best_match_score": round(max_sim * 100, 1),
                })

        return gaps


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

ai_service = AIService()
