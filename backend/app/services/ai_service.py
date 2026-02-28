"""
AI Service – Semantic Comparison Engine for ISO 27001 GRC Platform.

Loads ISO 27001 control descriptions, converts them into sentence embeddings,
and compares uploaded evidence text against them to find the best matches.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer
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
# Evidence category keywords
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
# Core AI Service
# ---------------------------------------------------------------------------

class AIService:
    """
    Semantic comparison engine for mapping evidence to ISO 27001 controls.

    On initialization:
      1. Loads control data from iso27001-controls.json
      2. Loads the sentence-transformer model
      3. Pre-computes embeddings for all 93 controls

    On each analysis request:
      1. Converts the input text to an embedding
      2. Computes cosine similarity against all control embeddings
      3. Returns top-N matches above a confidence threshold
    """

    MODEL_NAME = "all-MiniLM-L6-v2"
    DEFAULT_TOP_N = 5
    DEFAULT_THRESHOLD = 0.30  # minimum cosine similarity to consider a match

    def __init__(self, controls_path: Optional[str] = None):
        self._model: Optional[SentenceTransformer] = None
        self._controls: list[dict] = []
        self._control_texts: list[str] = []
        self._control_embeddings: Optional[np.ndarray] = None
        self._is_ready = False

        # Resolve the controls JSON path
        if controls_path:
            self._controls_path = Path(controls_path)
        else:
            # Default: look relative to the project root
            self._controls_path = (
                Path(__file__).resolve().parents[3]  # GRC main/
                / "src" / "data" / "iso27001-controls.json"
            )

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load model and pre-compute control embeddings. Call once at startup."""
        logger.info("AI Service: Loading ISO 27001 controls...")
        self._load_controls()

        logger.info(f"AI Service: Loading sentence-transformer model '{self.MODEL_NAME}'...")
        self._model = SentenceTransformer(self.MODEL_NAME)

        logger.info(f"AI Service: Computing embeddings for {len(self._controls)} controls...")
        self._control_embeddings = self._model.encode(
            self._control_texts, convert_to_numpy=True, show_progress_bar=False
        )

        self._is_ready = True
        logger.info("AI Service: Ready ✓")

    def _load_controls(self) -> None:
        """Load and parse the ISO 27001 controls JSON."""
        if not self._controls_path.exists():
            raise FileNotFoundError(
                f"Controls file not found: {self._controls_path}"
            )

        with open(self._controls_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._controls = data.get("controls", [])
        # Combine title + description for richer semantic matching
        self._control_texts = [
            f"{c['title']}. {c['description']}" for c in self._controls
        ]

    @property
    def is_ready(self) -> bool:
        return self._is_ready

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
        text_embedding = self._model.encode([text], convert_to_numpy=True)
        similarities = cosine_similarity(text_embedding, self._control_embeddings)[0]

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

    def _categorize(self, text: str) -> str:
        """Classify evidence into a category based on keyword matching."""
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score

        if scores:
            return max(scores, key=scores.get)
        return "general"

    # ------------------------------------------------------------------
    # Risk Suggestion
    # ------------------------------------------------------------------

    def suggest_risk_score(self, description: str) -> RiskSuggestion:
        """
        Analyze a risk description and suggest likelihood/impact scores.

        Uses semantic similarity to find related controls, then estimates
        risk based on how many controls are relevant and their domains.
        """
        if not self._is_ready:
            raise RuntimeError("AI Service not initialized. Call initialize() first.")

        # Find related controls
        text_embedding = self._model.encode([description], convert_to_numpy=True)
        similarities = cosine_similarity(text_embedding, self._control_embeddings)[0]
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

        # Heuristic scoring based on number and strength of related controls
        avg_relevance = np.mean(relevance_scores) if relevance_scores else 0.0
        num_controls = len(related_controls)

        # Higher relevance to more controls = potentially broader risk
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

        Returns a list of unmatched controls.
        """
        if not self._is_ready:
            raise RuntimeError("AI Service not initialized. Call initialize() first.")

        if not evidence_texts:
            return [
                {"control_id": c["id"], "annex": c["annex"], "title": c["title"]}
                for c in self._controls
            ]

        # Encode all evidence
        evidence_embeddings = self._model.encode(
            evidence_texts, convert_to_numpy=True, show_progress_bar=False
        )

        # For each control, check if ANY evidence matches above threshold
        gaps = []
        for idx, control in enumerate(self._controls):
            control_emb = self._control_embeddings[idx].reshape(1, -1)
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
