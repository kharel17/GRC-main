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
from typing import Optional, Any, Dict, List

from app.config import settings
from app.services.gemini_skills_adapter import GeminiSkillsAdapter

from google import genai
from google.genai import types
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# Re-exports for backward compatibility
# All consumers that do `from app.services.ai_service import X` will still work.
# ---------------------------------------------------------------------------
from app.services.ai_models import (
    ControlMatch,
    EvidenceAnalysisResult,
    DocumentAnalysisAIResult,
    RiskSuggestion,
    CATEGORY_KEYWORDS,
    ISO_DOMAIN_SYNONYMS,
)
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.document_analyzer import (
    _run_document_analysis_async,
    _extract_security_practices,
)

logger = logging.getLogger("grc.ai")


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
    GEMINI_GENERATE_MODEL = "gemini-3.8-flash"
    DEFAULT_TOP_N = 5
    DEFAULT_THRESHOLD = 0.30

    def __init__(self, controls_path: Optional[str] = None):
        # State
        self._controls: list[dict] = []
        self._control_texts: list[str] = []
        self._is_ready = False

        # Gemini skills engine & adapter
        self._gemini_client = None
        self._gemini_available = False
        self._gemini_control_embeddings: Optional[np.ndarray] = None
        self._skills_adapter: Optional[GeminiSkillsAdapter] = None

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
            self._skills_adapter = GeminiSkillsAdapter(
                client=self._gemini_client,
                controls=self._controls,
                model_name=self.GEMINI_GENERATE_MODEL,
            )
            logger.info("AI Service: Gemini generation client & Skills Adapter initialized ✓")

        except Exception as e:
            logger.warning(f"AI Service: Gemini init failed ({e}). Generator disabled.")
            self._gemini_available = False
            self._skills_adapter = GeminiSkillsAdapter(
                client=None,
                controls=self._controls,
                model_name=self.GEMINI_GENERATE_MODEL,
            )

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

    @property
    def skills_adapter(self) -> GeminiSkillsAdapter:
        """Returns the active GeminiSkillsAdapter instance (with fallback if offline)."""
        if self._skills_adapter is None:
            self._skills_adapter = GeminiSkillsAdapter(
                client=self._gemini_client,
                controls=self._controls,
                model_name=self.GEMINI_GENERATE_MODEL,
            )
        return self._skills_adapter

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
        dense_scores = cosine_similarity(text_embedding, control_embeddings)[0]  # type: ignore[arg-type]

        bm25_model = getattr(self, "_bm25_model", None)
        if bm25_model is not None:
            tokens = text.lower().split()
            bm25_scores = np.array(bm25_model.get_scores(tokens))
            bm25_max = float(bm25_scores.max())
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
        org_id: Optional[str] = None,
    ) -> EvidenceAnalysisResult:
        """
        Two-Tier Qdrant-backed evidence analysis:
        Tier 1: Queries tenant's ``grc_doc_chunks`` collection (scoped to org_id) for company internal policies.
        Tier 2: Queries global ``grc_iso_controls`` collection for standard ISO 27001 requirements.
        Synthesizes dual assessment: Evidence -> Internal Company Policy -> ISO 27001 Framework.

        Args:
            text: Extracted text of the evidence document.
            top_n: Maximum number of control matches to return.
            threshold: Minimum cosine similarity score (0.0 – 1.0).
            org_id: Organization ID for tenant-scoped internal policy retrieval.

        Returns:
            EvidenceAnalysisResult with two-tier evaluation findings and control matches.
        """
        if not self._is_ready:
            raise RuntimeError("AI Service not initialized. Call initialize() first.")

        # 1. Categorize the evidence
        category = self._categorize(text)

        from app.services.vector_store import vector_store

        # Qdrant Path
        if not vector_store.is_ready:
            raise RuntimeError(
                "Qdrant vector store is offline/unreachable. Evidence analysis cannot proceed in degraded mode."
            )

        text_embedding = self._embed_text(text)

        # Tier 2: Search ISO controls (global standard catalog)
        hits = await vector_store.dense_search(
            query_vector=text_embedding,
            collection_name=settings.QDRANT_COLLECTION_ISO_CONTROLS,
            top_k=min(top_n * 4, len(self._controls)),
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

        # Tier 1: Search Internal Policies in grc_doc_chunks (scoped by org_id)
        internal_policy_match: dict[str, Any] = {
            "found": False,
            "policy_title": None,
            "clause_summary": "No matching internal policy found for this organization.",
            "is_compliant_with_policy": False,
        }

        if org_id:
            try:
                policy_hits = await vector_store.dense_search(
                    query_vector=text_embedding,
                    collection_name=settings.QDRANT_COLLECTION_DOC_CHUNKS,
                    top_k=3,
                    org_id=str(org_id),
                )
                if policy_hits and float(policy_hits[0].get("score", 0.0)) >= threshold:
                    top_policy = policy_hits[0]
                    p_payload = top_policy.get("payload", {})
                    p_score = float(top_policy.get("score", 0.0))
                    p_title = p_payload.get("section_heading") or p_payload.get("document_id") or "Internal Policy"
                    raw_chunk_text = p_payload.get("text", "")
                    p_snippet = raw_chunk_text[:250].strip()
                    if len(raw_chunk_text) > 250:
                        p_snippet += "..."
                    internal_policy_match = {
                        "found": True,
                        "policy_title": p_title,
                        "clause_summary": p_snippet,
                        "is_compliant_with_policy": p_score >= 0.40,
                        "confidence_score": round(p_score, 2),
                    }
            except Exception as policy_search_err:
                logger.warning(f"Internal policy search in grc_doc_chunks failed: {policy_search_err}")

        # Framework control top match
        top_control = matched_controls[0] if matched_controls else None
        framework_control_match: dict[str, Any] = {
            "control_id": top_control.annex if top_control else None,
            "title": top_control.title if top_control else None,
            "is_compliant_with_framework": (top_control.confidence >= 50.0) if top_control else False,
            "confidence_score": round(top_control.confidence / 100.0, 2) if top_control else 0.0,
        }

        # Dual Assessment Gap Analysis
        if internal_policy_match["found"] and framework_control_match["control_id"]:
            if internal_policy_match["is_compliant_with_policy"] and framework_control_match["is_compliant_with_framework"]:
                gap_analysis = (
                    f"Evidence satisfies both internal policy ('{internal_policy_match['policy_title']}') "
                    f"and ISO 27001 requirements ({framework_control_match['control_id']} - {framework_control_match['title']})."
                )
            else:
                gap_analysis = (
                    f"Evidence maps to internal policy '{internal_policy_match['policy_title']}' and "
                    f"ISO 27001 control {framework_control_match['control_id']}, but compliance thresholds require review."
                )
        elif framework_control_match["control_id"]:
            gap_analysis = (
                f"Evidence aligns with ISO 27001 control {framework_control_match['control_id']} "
                f"({framework_control_match['title']}), but organization lacks an indexed internal policy clause for this domain."
            )
        elif internal_policy_match["found"]:
            gap_analysis = (
                f"Evidence matches internal policy '{internal_policy_match['policy_title']}', "
                "but does not strongly align with a standard ISO 27001 control."
            )
        else:
            gap_analysis = "Evidence could not be reliably mapped to internal policy or ISO 27001 controls."

        two_tier_evaluation = {
            "internal_policy_match": internal_policy_match,
            "framework_control_match": framework_control_match,
            "gap_analysis": gap_analysis,
        }

        # Formulate human-readable summary
        summary = f"[{category.capitalize()}] {gap_analysis}"

        return EvidenceAnalysisResult(
            category=category,
            matched_controls=matched_controls,
            summary=summary,
            internal_policy_match=internal_policy_match,
            framework_control_match=framework_control_match,
            two_tier_evaluation=two_tier_evaluation,
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
        """Deep analysis using Gemini Skills Adapter (gemini-3.8-flash)."""
        result = self.skills_adapter.process_compliance_document(text)
        return DocumentAnalysisAIResult(
            summary=result.get("summary", "Analysis completed."),
            category=result.get("category", "general"),
            implemented_controls=result.get("implemented_controls", []),
            missing_controls=result.get("missing_controls", []),
            security_practices=result.get("security_practices", []),
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
        """Use Gemini Skills Adapter to generate a structured risk score."""
        res = self.skills_adapter.analyze_risk(description, controls_context=self._controls)
        return RiskSuggestion(
            likelihood=res.get("likelihood", 3),
            impact=res.get("impact", 3),
            risk_score=res.get("risk_score", 9),
            reasoning=res.get("reasoning", "Assessed via Gemini Skills Adapter."),
            related_controls=res.get("related_controls", []),
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


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------

ai_service = AIService()
