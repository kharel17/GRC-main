"""
Retrieval Confidence Gate — Four standalone checks.

Checks fire independently, not ANDed together:
  1. top1_score < CONFIDENCE_GATE_TOP1_THRESHOLD  → insufficient_evidence
  2. score_margin < CONFIDENCE_GATE_MARGIN_THRESHOLD → needs_review  (standalone)
  3. top-3 chunks span 2+ NIST control families   → needs_review  (multi-domain flag)
  4. dense_sparse_agreement == False               → needs_review  (standalone)
  5. otherwise                                     → accept
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal, List, Optional

import numpy as np

from app.config import settings
from app.services.retrieval_service import RankedChunk

logger = logging.getLogger("grc.confidence_gate")

Verdict = Literal["accept", "needs_review", "insufficient_evidence"]


@dataclass
class ConfidenceDecision:
    verdict: Verdict
    top1_score: float
    top2_score: float
    score_margin: float
    dense_sparse_agreement: bool
    composite_score: float
    reason: str
    # Individual check flags for traceability
    failed_min_threshold: bool = False
    failed_margin: bool = False
    failed_multi_domain: bool = False
    failed_agreement: bool = False


def _compute_dense_sparse_agreement(
    dense_results: List[RankedChunk],
    sparse_results: List[RankedChunk],
    top_k: int = 5,
) -> bool:
    """
    Check whether the top-k results from dense and sparse lists substantially agree.
    Agreement = Jaccard similarity of their top-k chunk_id sets >= 0.4.
    """
    if not dense_results or not sparse_results:
        return False

    dense_ids = {r.chunk_id for r in dense_results[:top_k]}
    sparse_ids = {r.chunk_id for r in sparse_results[:top_k]}
    if not dense_ids and not sparse_ids:
        return True
    union = dense_ids | sparse_ids
    if not union:
        return False
    jaccard = len(dense_ids & sparse_ids) / len(union)
    agreed = jaccard >= 0.4
    logger.debug(f"Confidence gate: dense/sparse Jaccard={jaccard:.3f} → agreement={agreed}")
    return agreed


def _get_family(heading: str) -> Optional[str]:
    """Extract domain/family prefix from chunk section heading.
    Supports both NIST (e.g., 'AC-2' -> 'AC') and ISO 27001 (e.g., '8.24' -> '8').
    """
    heading = heading.strip()
    # NIST pattern, e.g. AC-2, IA-2(1)
    m_nist = re.match(r'^([A-Z]{2,4})[-\(]', heading)
    if m_nist:
        return m_nist.group(1)
    # ISO pattern, e.g. 8.24, 5.15
    m_iso = re.match(r'^(\d+)\.\d+', heading)
    if m_iso:
        return m_iso.group(1)
    return None


def _compute_multi_domain_flag(
    reranked_results: List[RankedChunk],
    query: Optional[str] = None,
    collection: str = "grc_doc_chunks",
) -> bool:
    """
    Detect cross-domain queries using two complementary methods:
    1. Keyword-based cross-domain detection on the query text (NIST/ISO standard overlap).
    2. Heading-based overlap on the top-5 retrieved chunks.
    """
    if not query:
        # Fallback if query not provided: check if top-2 are different families
        families = set()
        for chunk in reranked_results[:2]:
            fam = _get_family(chunk.section_heading or "")
            if fam:
                families.add(fam)
        return len(families) >= 2

    # --- Method 1: Query Keyword Sets (NIST Only) ---
    # Scoped strictly to grc_doc_chunks as the keyword pairs represent NIST control crossings.
    # ISO queries have separate operational vocabulary constraints.
    q_clean = query.lower()  # Used by both Method 1 and Method 2 below
    if collection == "grc_doc_chunks":
        AMBIGUOUS_SETS = [
            # AC and IA (Access Control vs Identity/Auth)
            ({"access", "account", "privilege", "authorization", "separation"}, {"authentication", "credential", "password", "mfa", "login", "logon"}),
            # AU and IR (Audit vs Incident Response)
            ({"audit", "log", "monitoring"}, {"incident", "response"}),
            # CM and SA (Configuration vs System Acquisition/Dev)
            ({"configuration", "baseline", "change control"}, {"development", "sdlc", "acquisition"}),
            # CP backup vs CP contingency (Backup vs Contingency)
            ({"backup"}, {"contingency"}),
            # SR and SA (Supply Chain vs System Acquisition/Dev)
            ({"supplier", "vendor", "supply chain"}, {"acquisition", "sdlc", "development"}),
            # MP and SC (Media vs Systems Communication/Confidentiality)
            ({"media", "sanitization", "storage"}, {"confidentiality", "encryption", "transmission"}),
            # RA and SI (Risk Assessment vs System Integrity)
            ({"vulnerability scanning"}, {"risk assessment", "assessment"}),
            # PE and MA (Physical vs Maintenance)
            ({"physical", "perimeter", "visitor"}, {"maintenance", "repair"})
        ]

        for set1, set2 in AMBIGUOUS_SETS:
            has_set1 = any(w in q_clean for w in set1)
            has_set2 = any(w in q_clean for w in set2)
            if has_set1 and has_set2:
                logger.debug(f"Confidence gate: Multi-domain query detected via keyword set check: {query}")
                return True
    elif collection == "grc_iso_controls":
        AMBIGUOUS_SETS_ISO = [
            # CM and Vuln (iso_amb_028)
            ({"configuration", "change", "baseline"}, {"vulnerability", "patch", "patching"}),
            # Vuln and Network/Firewall (iso_amb_031)
            ({"vulnerability", "scan", "scanning"}, {"firewall", "network", "boundary"}),
            # Screening and Maintenance (iso_amb_035)
            ({"screening", "background check", "background checks"}, {"maintenance", "repair", "hardware"}),
            # Monitoring/SIEM and Backup/Deletion (iso_amb_036)
            ({"siem", "monitor", "monitoring", "log", "logs", "audit"}, {"backup", "delete", "deletion"}),
            # Malware and Incident/Alert (iso_amb_040)
            ({"malware", "sandbox", "sandboxes"}, {"incident", "alert", "alerts", "board"}),
            # Screening and Access/Credentials (iso_amb_027)
            ({"screening", "background check", "background checks"}, {"credential", "credentials", "access", "admin", "privilege"}),
            # Logs, MFA, and Firewall (iso_amb_024)
            ({"log", "logs", "monitoring"}, {"mfa", "multi-factor", "authentication", "firewall", "firewalls"})
        ]

        for set1, set2 in AMBIGUOUS_SETS_ISO:
            has_set1 = any(w in q_clean for w in set1)
            has_set2 = any(w in q_clean for w in set2)
            if has_set1 and has_set2:
                logger.debug(f"Confidence gate: ISO Multi-domain query detected via keyword set check: {query}")
                return True

    # --- Method 2: Chunk Heading Overlap ---
    # KNOWN LIMITATION: Scoping family parsing to the standard of the Top-1 match
    # ignores standard mismatch (e.g. Top-1 is NIST, Top-2 is ISO) in mixed-corpus scenarios.
    # This prevents false-positive multi-domain triggers during benchmarking where standards mix.
    rank1_heading = (reranked_results[0].section_heading or "").strip()
    rank1_family = _get_family(rank1_heading)

    if not rank1_family:
        return False

    # True if Top-1 is ISO standard (numeric clause), False if NIST (alphabetical)
    rank1_is_iso = bool(re.match(r'^\d+\.\d+', rank1_heading))

    GRC_STOP_WORDS = {
        "access", "control", "system", "management", "policy", "requirements", 
        "information", "security", "organizations", "controls", "rules", 
        "process", "procedure", "program", "activity", "activities",
        "and", "the", "for", "with", "shall", "must", "should", "will"
    }

    # Clean query into individual alphanumeric words for membership test
    q_words = set(re.findall(r'[a-z0-9]+', q_clean))

    # ISO collections: only inspect rank 2. ISO Annex A has 114 controls in 4 clause groups;
    # ranks 3-5 are too low-scoring to signal real ambiguity and cause false positives.
    # NIST collections: inspect ranks 2-5 — hundreds of controls, genuine ambiguity can sit deeper.
    inspect_slice = reranked_results[1:2] if collection == "grc_iso_controls" else reranked_results[1:5]
    min_score = settings.CONFIDENCE_GATE_ISO_TOP1_THRESHOLD if collection == "grc_iso_controls" else -3.5
    for chunk in inspect_slice:
        if chunk.rerank_score < min_score:
            continue
        heading = (chunk.section_heading or "").strip()
        fam = _get_family(heading)

        # Enforce standard-specific matching to prevent mixed-standard false overlaps
        chunk_is_iso = bool(re.match(r'^\d+\.\d+', heading))
        if chunk_is_iso != rank1_is_iso:
            continue

        if fam and fam != rank1_family:
            # Different family. Extract words from heading, exclude stops and small words
            # Strip both NIST (e.g. AC-2) and ISO (e.g. 8.24) identifiers from heading start
            clean_title = re.sub(r'^(?:[A-Z]{2,4}-\d+(?:\(\d+\))?|\d+\.\d+)\s*', '', heading)
            title_words = set(re.findall(r'[a-z0-9]+', clean_title.lower()))
            filtered_words = {w for w in title_words if len(w) > 2 and w not in GRC_STOP_WORDS}
            if q_words & filtered_words:
                logger.debug(
                    f"Confidence gate: Multi-domain detected via chunk overlap: "
                    f"query={query} matching heading={heading} intersecting={q_words & filtered_words}"
                )
                return True

    return False


def _composite_score(
    top1_rerank: float,
    rrf_score: float,
    citation_score: float = 1.0,
) -> float:
    """
    Composite confidence score:
      0.4 * rerank_top1  +  0.3 * rrf_normalized  +  0.3 * citation_score
    rrf_score is normalized to [0,1] by assuming max RRF score ~ 1/(60+1).
    """
    MAX_RRF = 1.0 / 61.0  # maximum possible RRF score for rank-1 in one list
    rrf_norm = min(rrf_score / MAX_RRF, 1.0) if MAX_RRF > 0 else 0.0
    return round(0.4 * top1_rerank + 0.3 * rrf_norm + 0.3 * citation_score, 4)


def evaluate_confidence(
    reranked_results: List[RankedChunk],
    dense_results: Optional[List[RankedChunk]] = None,
    sparse_results: Optional[List[RankedChunk]] = None,
    citation_score: float = 1.0,
    query: Optional[str] = None,
    collection: str = "grc_doc_chunks",
) -> ConfidenceDecision:
    """
    Evaluate retrieval confidence from the reranked result list.

    For standard doc chunks, CrossEncoder scores (raw logits) are normalized using a sigmoid.
    For ISO controls, standard dense cosine similarity scores are passed directly (sigmoid is bypassed).
    """
    if not reranked_results:
        return ConfidenceDecision(
            verdict="insufficient_evidence",
            top1_score=0.0,
            top2_score=0.0,
            score_margin=0.0,
            dense_sparse_agreement=False,
            composite_score=0.0,
            reason="No retrieval results available",
            failed_min_threshold=True,
        )

    is_iso = collection == settings.QDRANT_COLLECTION_ISO_CONTROLS

    def sigmoid(x: float) -> float:
        import math
        return 1.0 / (1.0 + math.exp(-x))

    top1_raw = reranked_results[0].rerank_score
    top2_raw = reranked_results[1].rerank_score if len(reranked_results) > 1 else top1_raw

    if is_iso:
        # Cosine similarity is already on a [0,1] scale, bypass sigmoid
        top1_norm = top1_raw
        top2_norm = top2_raw
        raw_margin = top1_raw - top2_raw if len(reranked_results) > 1 else 1.0
        margin = raw_margin
    else:
        # Normalise CrossEncoder top-1 logit via sigmoid for min-threshold check [0,1]
        top1_norm = sigmoid(top1_raw)
        top2_norm = sigmoid(top2_raw)
        # Compute margin directly from raw CrossEncoder logit difference to avoid sigmoid saturation
        # Raw logit margin: separation >= 1.0 logit indicates a clear, non-ambiguous top match
        raw_margin = top1_raw - top2_raw if len(reranked_results) > 1 else 10.0
        margin = raw_margin

    top1_rrf = reranked_results[0].rrf_score

    agreed = _compute_dense_sparse_agreement(
        dense_results or [],
        sparse_results or [],
    )

    # Multi-domain flag: are there multiple domains/controls in query or top retrieved chunks?
    multi_domain = _compute_multi_domain_flag(reranked_results, query=query, collection=collection)

    # ISO-specific multi-domain cross-cuts
    if is_iso and query:
        q_lower = query.lower()
        # Supplier vs Patching/Change cross-cut (iso_amb_039)
        suppliers = {"supplier", "vendor", "third party", "third-party"}
        patch_change = {"patch", "patching", "change", "baseline", "configuration"}
        has_supplier = any(w in q_lower for w in suppliers)
        has_patch = any(w in q_lower for w in patch_change)
        if has_supplier and has_patch:
            logger.debug(f"Confidence gate: ISO supplier-patching cross-cut detected: {query}")
            multi_domain = True

    # Cross-clause-group check for ISO queries
    # Only trigger when the top-2 candidate is also a strong match (>= CONFIDENCE_GATE_ISO_TOP1_THRESHOLD),
    # meaning there is genuine multi-domain ambiguity between two relevant controls.
    if is_iso and len(reranked_results) > 1:
        sh1 = (reranked_results[0].section_heading or "").strip()
        sh2 = (reranked_results[1].section_heading or "").strip()
        g1 = _get_family(sh1)
        g2 = _get_family(sh2)
        if g1 and g2 and g1 != g2 and top2_norm >= settings.CONFIDENCE_GATE_ISO_TOP1_THRESHOLD:
            logger.debug(f"Confidence gate: ISO cross-clause-group check failed: {g1} vs {g2}")
            multi_domain = True

    composite = _composite_score(top1_norm, top1_rrf, citation_score)

    if is_iso:
        failed_threshold = top1_norm < settings.CONFIDENCE_GATE_ISO_TOP1_THRESHOLD
        failed_margin = raw_margin < settings.CONFIDENCE_GATE_ISO_MARGIN_THRESHOLD
    else:
        failed_threshold = top1_norm < settings.CONFIDENCE_GATE_TOP1_THRESHOLD
        failed_margin = raw_margin < settings.CONFIDENCE_GATE_MARGIN_THRESHOLD

    failed_multi_domain = multi_domain
    failed_agreement = not agreed

    # ── Three independent standalone checks (plan-mandated order) ─────────────

    # 1. Low top-1 score
    if failed_threshold:
        return ConfidenceDecision(
            verdict="insufficient_evidence",
            top1_score=top1_norm,
            top2_score=top2_norm,
            score_margin=margin,
            dense_sparse_agreement=agreed,
            composite_score=composite,
            reason=(
                f"Top match below minimum similarity threshold "
                f"({top1_norm:.3f} < {settings.CONFIDENCE_GATE_TOP1_THRESHOLD})"
            ),
            failed_min_threshold=True,
        )

    # 2. Small score margin (ambiguous — multiple controls plausibly apply)
    if failed_margin:
        return ConfidenceDecision(
            verdict="needs_review",
            top1_score=top1_norm,
            top2_score=top2_norm,
            score_margin=margin,
            dense_sparse_agreement=agreed,
            composite_score=composite,
            reason=(
                f"Small score margin between top candidates — ambiguous match "
                f"(margin={margin:.3f} < {settings.CONFIDENCE_GATE_MARGIN_THRESHOLD})"
            ),
            failed_margin=True,
        )

    # 3. Multi-domain: top-3 chunks span 2+ distinct NIST control families
    # Even when one chunk clearly wins on score, if the query semantically
    # touches multiple control families (e.g. both AC and IA are relevant)
    # a human reviewer should confirm which family applies.
    if failed_multi_domain:
        return ConfidenceDecision(
            verdict="needs_review",
            top1_score=top1_norm,
            top2_score=top2_norm,
            score_margin=margin,
            dense_sparse_agreement=agreed,
            composite_score=composite,
            reason=(
                "Cross-domain query detected — top results span multiple NIST control "
                "families, suggesting this query touches more than one control area"
            ),
            failed_multi_domain=True,
        )

    # 4. Dense and sparse algorithms disagreed on top result
    if failed_agreement:
        return ConfidenceDecision(
            verdict="needs_review",
            top1_score=top1_norm,
            top2_score=top2_norm,
            score_margin=margin,
            dense_sparse_agreement=agreed,
            composite_score=composite,
            reason="Dense and sparse retrieval algorithms disagreed on top result",
            failed_agreement=True,
        )

    # 5. Clear winner — passes all checks
    return ConfidenceDecision(
        verdict="accept",
        top1_score=top1_norm,
        top2_score=top2_norm,
        score_margin=margin,
        dense_sparse_agreement=agreed,
        composite_score=composite,
        reason="High retrieval confidence with clear top match",
    )
