"""
Swappable LLM Backend — local-only / self-hosted / cloud.

LLM_MODE controls which backend is active:
  "local-only"   — sentence-transformers extractive summarisation + local keyword heuristics.
                   No external calls. Always available.
  "self-hosted"  — Ollama-compatible REST endpoint (LLM_SELF_HOSTED_BASE_URL).
                   Falls back to local-only if endpoint unreachable.
  "cloud"        — Google Gemini via google-generativeai SDK.
                   Blocked at startup in DATA_RESIDENCY_MODE=strict.

All backends implement the same interface:
  generate_structured(prompt, context_chunks) -> LLMResult
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("grc.llm_backend")


# ── Result type ────────────────────────────────────────────────────────────────

@dataclass
class LLMResult:
    summary: str
    document_category: str
    implemented_controls: List[str] = field(default_factory=list)
    missing_controls: List[str] = field(default_factory=list)
    security_practices: List[str] = field(default_factory=list)
    cited_chunk_ids: List[str] = field(default_factory=list)
    backend_used: str = "unknown"
    raw_response: Optional[str] = None


# ── Local-Only Backend ────────────────────────────────────────────────────────

class LocalOnlyBackend:
    """
    Extractive summarisation using the already-loaded ai_service.
    No external calls. Used when LLM_MODE='local-only' or as fallback.
    """
    name = "local-only"

    def generate_structured(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> LLMResult:
        from app.services.ai_service import ai_service, _run_document_analysis

        full_text = "\n\n".join(c.get("text", "") for c in context_chunks)
        if not full_text.strip():
            return LLMResult(
                summary="No context available for analysis.",
                document_category="general",
                backend_used=self.name,
            )

        try:
            analysis = _run_document_analysis(full_text)
        except Exception as e:
            logger.warning(f"LocalOnlyBackend: _run_document_analysis failed ({e})")
            analysis = {}

        # Extractive summary: first 3 sentences of the combined context
        sentences = re.split(r'(?<=[.!?])\s+', full_text.strip())
        summary = " ".join(sentences[:3]).strip()
        if not summary:
            summary = full_text[:300].strip()

        return LLMResult(
            summary=summary,
            document_category=analysis.get("document_category", "general"),
            implemented_controls=analysis.get("implemented_controls", []),
            missing_controls=analysis.get("missing_controls", []),
            security_practices=analysis.get("security_practices", []),
            cited_chunk_ids=[c.get("chunk_id", "") for c in context_chunks[:3]],
            backend_used=self.name,
            raw_response=None,
        )


# ── Self-Hosted Backend (Ollama-compatible) ──────────────────────────────────

class SelfHostedBackend:
    """
    Calls an Ollama-compatible REST endpoint: POST /api/generate.
    Falls back to LocalOnlyBackend if the endpoint is unreachable.
    """
    name = "self-hosted"

    def __init__(self):
        self._fallback = LocalOnlyBackend()

    def _build_prompt(self, prompt: str, context_chunks: List[Dict[str, Any]]) -> str:
        context = "\n\n---\n\n".join(
            f"[Chunk {c.get('chunk_id', 'unknown')} | {c.get('section_heading', '')}]\n{c.get('text', '')}"
            for c in context_chunks[:8]
        )
        return (
            f"{prompt}\n\n"
            f"=== Retrieved Context ===\n{context}\n\n"
            "=== Instructions ===\n"
            "Based on the context above, respond with a JSON object containing:\n"
            '  "summary": string,\n'
            '  "document_category": string,\n'
            '  "implemented_controls": [list of ISO 27001 annex IDs],\n'
            '  "missing_controls": [list of ISO 27001 annex IDs],\n'
            '  "security_practices": [list of strings],\n'
            '  "cited_chunk_ids": [list of chunk IDs from context]\n'
            "Respond with valid JSON only."
        )

    def generate_structured(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> LLMResult:
        import httpx

        base_url = settings.LLM_SELF_HOSTED_BASE_URL
        if not base_url:
            logger.warning("SelfHostedBackend: LLM_SELF_HOSTED_BASE_URL not set; falling back to local")
            return self._fallback.generate_structured(prompt, context_chunks)

        full_prompt = self._build_prompt(prompt, context_chunks)
        payload = {
            "model": settings.LLM_SELF_HOSTED_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "format": "json",
        }

        try:
            response = httpx.post(
                f"{base_url.rstrip('/')}/api/generate",
                json=payload,
                timeout=120.0,
            )
            response.raise_for_status()
            raw = response.json().get("response", "")
            data = json.loads(raw)
            return LLMResult(
                summary=data.get("summary", ""),
                document_category=data.get("document_category", "general"),
                implemented_controls=data.get("implemented_controls", []),
                missing_controls=data.get("missing_controls", []),
                security_practices=data.get("security_practices", []),
                cited_chunk_ids=data.get("cited_chunk_ids", []),
                backend_used=self.name,
                raw_response=raw,
            )
        except Exception as e:
            logger.warning(f"SelfHostedBackend: request to '{base_url}' failed ({e}); falling back to local")
            result = self._fallback.generate_structured(prompt, context_chunks)
            result.backend_used = f"{self.name}->fallback:{self._fallback.name}"
            return result


# ── Cloud Backend (Google Gemini) ─────────────────────────────────────────────

class CloudBackend:
    """
    Google Gemini via the google-generativeai SDK.
    Raises RuntimeError at construction if DATA_RESIDENCY_MODE=strict.
    """
    name = "cloud"

    def __init__(self):
        if settings.DATA_RESIDENCY_MODE == "strict":
            # This should have been caught by the startup validator, but double-guard here
            raise RuntimeError(
                "CloudBackend cannot be used in DATA_RESIDENCY_MODE=strict. "
                "Set LLM_MODE to 'local-only' or 'self-hosted'."
            )
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("CloudBackend requires GEMINI_API_KEY to be set.")

        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(settings.LLM_CLOUD_MODEL)
        self._fallback = LocalOnlyBackend()

    def _build_prompt(self, prompt: str, context_chunks: List[Dict[str, Any]]) -> str:
        context = "\n\n---\n\n".join(
            f"[Chunk {c.get('chunk_id', 'unknown')} | {c.get('section_heading', '')}]\n{c.get('text', '')}"
            for c in context_chunks[:8]
        )
        return (
            f"{prompt}\n\n"
            f"=== Retrieved Context ===\n{context}\n\n"
            "=== Instructions ===\n"
            "Based on the context above, respond with a JSON object containing:\n"
            '  "summary": string,\n'
            '  "document_category": string,\n'
            '  "implemented_controls": [list of ISO 27001 annex IDs],\n'
            '  "missing_controls": [list of ISO 27001 annex IDs],\n'
            '  "security_practices": [list of strings],\n'
            '  "cited_chunk_ids": [list of chunk IDs from context]\n'
            "Respond with valid JSON only, no markdown fences."
        )

    def generate_structured(
        self,
        prompt: str,
        context_chunks: List[Dict[str, Any]],
    ) -> LLMResult:
        full_prompt = self._build_prompt(prompt, context_chunks)
        try:
            response = self._model.generate_content(full_prompt)
            raw = response.text.strip()
            # Strip any accidental markdown fences
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("` \n")
            data = json.loads(raw)
            return LLMResult(
                summary=data.get("summary", ""),
                document_category=data.get("document_category", "general"),
                implemented_controls=data.get("implemented_controls", []),
                missing_controls=data.get("missing_controls", []),
                security_practices=data.get("security_practices", []),
                cited_chunk_ids=data.get("cited_chunk_ids", []),
                backend_used=self.name,
                raw_response=raw,
            )
        except Exception as e:
            logger.warning(f"CloudBackend: Gemini call failed ({e}); falling back to local")
            result = self._fallback.generate_structured(prompt, context_chunks)
            result.backend_used = f"{self.name}->fallback:{self._fallback.name}"
            return result


# ── Factory + Singleton ───────────────────────────────────────────────────────

def _create_backend() -> LocalOnlyBackend | SelfHostedBackend | CloudBackend:
    mode = settings.LLM_MODE
    logger.info(f"LLM backend: creating backend for LLM_MODE='{mode}'")
    if mode == "cloud":
        try:
            return CloudBackend()
        except Exception as e:
            logger.warning(f"CloudBackend init failed ({e}); defaulting to local-only")
            return LocalOnlyBackend()
    elif mode == "self-hosted":
        return SelfHostedBackend()
    else:
        return LocalOnlyBackend()


# Singleton — created lazily to allow data_residency validator to run first
_backend_instance: Optional[LocalOnlyBackend | SelfHostedBackend | CloudBackend] = None


def get_llm_backend() -> LocalOnlyBackend | SelfHostedBackend | CloudBackend:
    """Return the singleton LLM backend, creating it on first call."""
    global _backend_instance
    if _backend_instance is None:
        _backend_instance = _create_backend()
    return _backend_instance
