"""
Gemini Skills Adapter for GRC.

Integrates skills and utilities from `tools/gemini_skills` (Google Gemini Skills Library)
into the FastAPI backend AI pipeline and developer tooling.

Skills supported:
- `process_compliance_document`: Deep structured document compliance analysis (Step 3).
- `map_controls`: ISO 27001:2022 Annex A control mapping with confidence & rationale.
- `analyze_risk`: Quantitative & qualitative risk scoring with control mitigation.
- `audit_codebase`: Security & architectural audit persona for Senior AppSec & Lead Developer.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from google import genai

logger = logging.getLogger("grc.gemini_skills")

# Add tools/gemini_skills path dynamically for helper imports
PROJECT_ROOT = Path(__file__).resolve().parents[3]
GEMINI_SKILLS_PATH = PROJECT_ROOT / "tools" / "gemini_skills"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(GEMINI_SKILLS_PATH) not in sys.path:
    sys.path.insert(0, str(GEMINI_SKILLS_PATH))

# Attempt to load helper utilities from gemini_skills repo
try:
    from tools.gemini_skills.skills.gemini_omni_flash_api.scripts.upload_file import (  # type: ignore
        sanitize_error,
        detect_mime_type,
        strip_query_params,
    )
except ImportError:
    # Fallback to direct path or local implementation if folder names have hyphens
    try:
        import importlib.util
        upload_script_path = (
            GEMINI_SKILLS_PATH
            / "skills"
            / "gemini-omni-flash-api"
            / "scripts"
            / "upload_file.py"
        )
        if upload_script_path.exists():
            spec = importlib.util.spec_from_file_location("upload_file_mod", str(upload_script_path))
            if spec is not None and spec.loader is not None:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                sanitize_error = mod.sanitize_error
                detect_mime_type = mod.detect_mime_type
                strip_query_params = mod.strip_query_params
            else:
                raise ImportError(f"Could not load module specification from {upload_script_path}")
        else:
            raise FileNotFoundError("upload_file.py not found in gemini-omni-flash-api")
    except Exception as e:
        logger.warning(f"Could not import upload_file helpers from gemini_skills: {e}")

        def sanitize_error(err: Any) -> str:
            msg = str(err)
            msg = re.sub(r'AIza[0-9A-Za-z_\-]{30,}', '[REDACTED_KEY]', msg)
            return msg[:400]

        def detect_mime_type(file_path: str) -> str:
            return "application/pdf" if file_path.endswith(".pdf") else "text/plain"

        def strip_query_params(url: str) -> str:
            return url.split("?")[0] if url else ""


class GeminiSkillsAdapter:
    """
    Adapter interfacing the official Google Gemini Skills specification with the GRC backend.
    
    Adheres to the official gemini-api-dev skill guidelines:
    - Primary model: `gemini-3.8-flash` (replaces deprecated 1.5/2.0 series)
    - Structured JSON output schemas
    - Sanitized error handling and safe execution
    - Resilient offline heuristic fallbacks when API is unreachable
    """

    DEFAULT_MODEL = "gemini-3.8-flash"

    def __init__(
        self,
        client: Optional[Any] = None,
        controls: Optional[List[Dict[str, Any]]] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.client = client
        self.controls = controls or []
        self.model_name = model_name or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)

    @property
    def is_gemini_active(self) -> bool:
        return self.client is not None

    # -------------------------------------------------------------------------
    # Skill 1: Document Processing (process_compliance_document)
    # -------------------------------------------------------------------------
    def process_compliance_document(
        self, text: str, filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deep analysis of security documents (policies, procedures, audit reports)
        extracting compliance controls, missing requirements, and observed security practices.
        """
        if not text or not text.strip():
            return {
                "summary": "Empty document provided.",
                "category": "general",
                "implemented_controls": [],
                "missing_controls": [],
                "security_practices": [],
            }

        client = self.client
        if client is not None:
            try:
                from google.genai import types

                prompt = f"""You are an ISO 27001 Lead Auditor and GRC Security Architect.
Analyze the following security document text and extract structured compliance data.

Document Filename: {filename or 'Unknown'}
Document Content Excerpt:
{text[:9000]}

Respond ONLY with a valid JSON object formatted exactly as:
{{
  "summary": "<concise executive summary of policy purpose and scope>",
  "category": "<policy|procedure|architecture|standard|log|report>",
  "security_practices": [
    {{"practice": "<name of practice>", "excerpt": "<brief quotation/reference>", "strength": "strong|partial|informational"}}
  ],
  "implemented_controls": [
    {{"annex": "<e.g. 5.1>", "title": "<control title>", "confidence": <float 0.0-1.0>, "reason": "<evidence found in text>"}}
  ],
  "missing_controls": [
    {{"annex": "<e.g. 8.12>", "title": "<control title>", "reason": "<why this control logically belongs here but is absent>"}}
  ]
}}"""

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )

                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
                return json.loads(raw_text)

            except Exception as exc:
                clean_err = sanitize_error(exc)
                logger.warning(f"Gemini process_compliance_document failed ({clean_err}), using heuristic fallback")

        # Fallback heuristic
        return self._heuristic_document_analysis(text)

    def _heuristic_document_analysis(self, text: str) -> Dict[str, Any]:
        """Local heuristic parser for document compliance."""
        text_lower = text.lower()
        category = "policy" if "policy" in text_lower else "procedure" if "procedure" in text_lower else "general"
        practices = []
        if "mfa" in text_lower or "multi-factor" in text_lower:
            practices.append({"practice": "Multi-factor authentication (MFA)", "excerpt": "MFA requirements mentioned", "strength": "strong"})
        if "encrypt" in text_lower or "aes-256" in text_lower or "tls" in text_lower:
            practices.append({"practice": "Cryptographic protection", "excerpt": "Encryption protocols identified", "strength": "strong"})
        if "log" in text_lower or "siem" in text_lower or "monitoring" in text_lower:
            practices.append({"practice": "Audit logging & monitoring", "excerpt": "Logging references found", "strength": "partial"})

        return {
            "summary": f"Compliance assessment of {category} document (heuristic engine).",
            "category": category,
            "implemented_controls": [],
            "missing_controls": [],
            "security_practices": practices,
        }

    # -------------------------------------------------------------------------
    # Skill 2: Control Mapping (map_controls)
    # -------------------------------------------------------------------------
    def map_controls(
        self,
        text: str,
        candidate_controls: Optional[List[Dict[str, Any]]] = None,
        top_n: int = 5,
        threshold: float = 0.30,
    ) -> List[Dict[str, Any]]:
        """
        Maps evidence text against ISO 27001 controls with confidence scores and audit justifications.
        """
        controls_pool = candidate_controls or self.controls
        if not controls_pool:
            return []

        client = self.client
        if client is not None:
            try:
                from google.genai import types

                sample_controls = [
                    f"- Annex {c.get('annex', c.get('id', ''))}: {c.get('title', '')} - {c.get('description', '')[:120]}"
                    for c in controls_pool[:40]
                ]
                controls_str = "\n".join(sample_controls)

                prompt = f"""You are an ISO 27001 Compliance Auditor.
Given the following evidence/document text, map it to the top {top_n} most relevant ISO 27001 controls from the candidate list.

Evidence Text:
{text[:4000]}

Candidate Controls:
{controls_str}

Return ONLY a valid JSON array of objects with the structure:
[
  {{
    "control_id": "<id or annex>",
    "annex": "<annex id>",
    "title": "<title>",
    "description": "<brief description>",
    "confidence": <float 0.0-1.0>,
    "rationale": "<specific justification citing the evidence text>"
  }}
]"""

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )

                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
                matches = json.loads(raw_text)
                return [m for m in matches if float(m.get("confidence", 0)) >= threshold][:top_n]

            except Exception as exc:
                clean_err = sanitize_error(exc)
                logger.warning(f"Gemini map_controls failed ({clean_err}), using keyword heuristic")

        # Heuristic fallback
        text_lower = text.lower()
        scored: List[Dict[str, Any]] = []
        for c in controls_pool:
            title = c.get("title", "").lower()
            desc = c.get("description", "").lower()
            pool_words = set((title + " " + desc).split())
            overlap = sum(1 for word in pool_words if len(word) > 3 and word in text_lower)
            if overlap > 0:
                conf = min(0.95, round(0.3 + (overlap * 0.15), 2))
                if conf >= threshold:
                    scored.append({
                        "control_id": c.get("id", ""),
                        "annex": c.get("annex", c.get("id", "")),
                        "title": c.get("title", ""),
                        "description": c.get("description", ""),
                        "confidence": conf,
                        "rationale": f"Matched keywords in control title: '{c.get('title')}'",
                    })
        scored.sort(key=lambda x: x["confidence"], reverse=True)
        return scored[:top_n]

    # -------------------------------------------------------------------------
    # Skill 3: Risk Analysis (analyze_risk)
    # -------------------------------------------------------------------------
    def analyze_risk(
        self,
        description: str,
        controls_context: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Performs ISO 27005 / ISO 31000 qualitative risk analysis: likelihood (1-5),
        impact (1-5), composite risk score, reasoning, and mitigating controls.
        """
        if not description or not description.strip():
            return {
                "likelihood": 1,
                "impact": 1,
                "risk_score": 1,
                "reasoning": "No description provided.",
                "related_controls": [],
            }

        controls_pool = controls_context or self.controls
        control_list = "\n".join(
            f"- {c.get('annex', c.get('id', ''))}: {c.get('title', '')}"
            for c in controls_pool[:30]
        )

        client = self.client
        if client is not None:
            try:
                from google.genai import types

                prompt = f"""You are an ISO 27005 Risk Assessment Specialist.
Analyze the following risk description and provide a formal risk scoring and mitigation analysis.

Risk Description:
{description}

Available ISO 27001 Controls:
{control_list}

Respond with ONLY a valid JSON object matching this schema:
{{
  "likelihood": <integer 1-5 (1=Rare, 2=Unlikely, 3=Possible, 4=Likely, 5=Almost Certain)>,
  "impact": <integer 1-5 (1=Insignificant, 2=Minor, 3=Moderate, 4=Major, 5=Catastrophic)>,
  "risk_score": <integer = likelihood * impact>,
  "reasoning": "<concise risk assessment rationale>",
  "related_controls": ["<Annex_ID> <Control_Title>", ...]
}}"""

                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )

                raw = response.text.strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                res = json.loads(raw)
                l = max(1, min(5, int(res.get("likelihood", 3))))
                i = max(1, min(5, int(res.get("impact", 3))))
                return {
                    "likelihood": l,
                    "impact": i,
                    "risk_score": l * i,
                    "reasoning": res.get("reasoning", "Assessed via Gemini 3.8 Flash"),
                    "related_controls": res.get("related_controls", []),
                }

            except Exception as exc:
                clean_err = sanitize_error(exc)
                logger.warning(f"Gemini analyze_risk failed ({clean_err}), using default risk matrix")

        # Heuristic fallback
        desc_lower = description.lower()
        likelihood = 3
        impact = 3
        if any(w in desc_lower for w in ["critical", "catastrophic", "breach", "zero-day", "ransomware"]):
            impact = 5
        elif any(w in desc_lower for w in ["major", "severe", "downtime", "leak"]):
            impact = 4

        if any(w in desc_lower for w in ["frequent", "continuous", "daily", "high exposure"]):
            likelihood = 4
        elif any(w in desc_lower for w in ["rare", "isolated", "internal-only"]):
            likelihood = 2

        return {
            "likelihood": likelihood,
            "impact": impact,
            "risk_score": likelihood * impact,
            "reasoning": "Heuristic risk score computed from keyword severity.",
            "related_controls": ["5.1 Policies for information security", "8.8 Management of technical vulnerabilities"],
        }

    # -------------------------------------------------------------------------
    # Skill 4: Codebase Security Auditor (audit_codebase)
    # -------------------------------------------------------------------------
    def audit_codebase(
        self,
        target_dirs: Optional[List[str]] = None,
        persona: str = "Senior AppSec & Lead Developer",
    ) -> Dict[str, Any]:
        """
        Inspects the codebase for security anti-patterns:
        - SQL/RLS injection risk
        - Authentication & authorization leaks
        - Uncaught async exceptions / unhandled promises
        - Hardcoded credentials / secret tokens
        """
        from backend.scripts.audit.code_auditor import run_static_security_audit  # type: ignore

        dirs_to_scan = target_dirs or ["backend", "src"]
        audit_results = run_static_security_audit(
            project_root=str(PROJECT_ROOT),
            target_dirs=dirs_to_scan,
        )

        return {
            "persona": persona,
            "target_dirs": dirs_to_scan,
            "summary": audit_results.get("summary", {}),
            "findings": audit_results.get("findings", []),
            "remediations": audit_results.get("remediations", []),
        }

    # -------------------------------------------------------------------------
    # Tool Schemas for Gemini & MCP Tool Registration
    # -------------------------------------------------------------------------
    @classmethod
    def get_tool_declarations(cls) -> List[Dict[str, Any]]:
        """Returns tool declarations suitable for Gemini Function Calling."""
        return [
            {
                "name": "process_compliance_document",
                "description": "Analyze compliance documents, extract security practices, implemented controls, and missing controls.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "text": {"type": "STRING", "description": "The extracted text of the document to analyze."},
                        "filename": {"type": "STRING", "description": "Optional name of the document."},
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "map_controls",
                "description": "Map an excerpt or evidence item against ISO 27001 Annex A controls.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "text": {"type": "STRING", "description": "Evidence or requirement text."},
                        "top_n": {"type": "INTEGER", "description": "Maximum number of control matches to return."},
                        "threshold": {"type": "NUMBER", "description": "Minimum similarity/confidence threshold between 0.0 and 1.0."},
                    },
                    "required": ["text"],
                },
            },
            {
                "name": "analyze_risk",
                "description": "Calculate likelihood, impact, composite risk score, and ISO 27001 mitigations for a risk scenario.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "description": {"type": "STRING", "description": "Detailed description of the risk scenario."},
                    },
                    "required": ["description"],
                },
            },
            {
                "name": "audit_codebase",
                "description": "Audit backend and frontend source directories for security vulnerabilities and code health.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "target_dirs": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "List of directories to audit, e.g. ['backend', 'src'].",
                        },
                    },
                },
            },
        ]

    @classmethod
    def get_mcp_tools(cls) -> List[Dict[str, Any]]:
        """Returns tool definitions in Model Context Protocol (MCP) format."""
        declarations = cls.get_tool_declarations()
        mcp_tools = []
        for decl in declarations:
            params = decl.get("parameters", {})
            properties = {}
            for prop_name, prop_def in params.get("properties", {}).items():
                p_type = prop_def.get("type", "string").lower()
                properties[prop_name] = {
                    "type": "array" if p_type == "array" else "number" if p_type in ["number", "integer"] else "string",
                    "description": prop_def.get("description", ""),
                }
            mcp_tools.append({
                "name": decl["name"],
                "description": decl["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": params.get("required", []),
                },
            })
        return mcp_tools
