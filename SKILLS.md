# GRC Gemini Skills & Tools Directives

This document details the Google Gemini Skills library integrated into this repository from `https://github.com/google-gemini/gemini-skills` (`tools/gemini_skills`), how to invoke them, their argument schemas, and execution patterns via the backend Python virtual environment.

---

## 1. Directory Structure

```
GRC-main/
├── tools/
│   └── gemini_skills/            # Cloned official google-gemini/gemini-skills
│       ├── skills/
│       │   ├── gemini-api-dev/       # Interactions API, models, structured outputs
│       │   ├── gemini-live-api-dev/  # Real-time WebSocket streaming
│       │   └── gemini-omni-flash-api/# Video/multimodal processing & file upload scripts
├── backend/
│   ├── app/
│   │   └── services/
│   │       ├── gemini_skills_adapter.py # Bridge between skills and GRC AI pipelines
│   │       └── ai_service.py            # Primary AI orchestration engine
│   └── scripts/
│       ├── audit/
│       │   └── code_auditor.py          # Senior AppSec & Lead Dev security auditor
│       └── test_gemini_skills.py        # Verification & test suite
└── SKILLS.md                            # This specification
```

---

## 2. Model Policy & Deprecations

As mandated by `tools/gemini_skills/skills/gemini-api-dev/SKILL.md`:
- **Active Production Model**: `gemini-3.8-flash` (balanced agentic & multimodal execution).
- **High-Throughput Model**: `gemini-3.5-flash-lite`.
- **Reasoning & Complex Tasks**: `gemini-3.1-pro-preview`.
- **DEPRECATED**: `gemini-2.5-*`, `gemini-2.0-*`, `gemini-1.5-*` are legacy. All backend calls default to `gemini-3.8-flash`.

---

## 3. Available GRC Skills & Tool Schemas

All skills can be accessed programmatically via `GeminiSkillsAdapter` (`backend.app.services.gemini_skills_adapter`), registered as Gemini Function Declarations, or executed as Model Context Protocol (MCP) tools.

### Skill 1: `process_compliance_document`
- **Purpose**: Deep compliance analysis of security policies, SOPs, and audit reports.
- **Invocation**:
  ```python
  from app.services.gemini_skills_adapter import GeminiSkillsAdapter
  adapter = GeminiSkillsAdapter(client=gemini_client)
  result = adapter.process_compliance_document(text="Document body...", filename="Access_Policy.pdf")
  ```
- **Argument Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "text": {"type": "string", "description": "Extracted text of the security document."},
      "filename": {"type": "string", "description": "Optional original filename."}
    },
    "required": ["text"]
  }
  ```
- **Output Schema**:
  ```json
  {
    "summary": "string",
    "category": "policy | procedure | architecture | standard | log | report",
    "security_practices": [
      {"practice": "string", "excerpt": "string", "strength": "strong | partial | informational"}
    ],
    "implemented_controls": [
      {"annex": "string", "title": "string", "confidence": 0.95, "reason": "string"}
    ],
    "missing_controls": [
      {"annex": "string", "title": "string", "reason": "string"}
    ]
  }
  ```

---

### Skill 2: `map_controls`
- **Purpose**: Maps evidence or text requirements against ISO 27001:2022 Annex A controls.
- **Invocation**:
  ```python
  matches = adapter.map_controls(text="We require MFA across all user logins", top_n=3, threshold=0.4)
  ```
- **Argument Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "text": {"type": "string", "description": "Evidence or requirement excerpt."},
      "top_n": {"type": "integer", "description": "Max matches to return (default: 5)."},
      "threshold": {"type": "number", "description": "Minimum confidence cutoff 0.0-1.0 (default: 0.30)."}
    },
    "required": ["text"]
  }
  ```

---

### Skill 3: `analyze_risk`
- **Purpose**: Calculates quantitative likelihood (1-5), impact (1-5), composite risk score, and maps mitigating controls.
- **Invocation**:
  ```python
  risk = adapter.analyze_risk("Unencrypted backup tapes stored in offsite facility without CCTV.")
  ```
- **Argument Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "description": {"type": "string", "description": "Detailed risk scenario."}
    },
    "required": ["description"]
  }
  ```
- **Output Schema**:
  ```json
  {
    "likelihood": 4,
    "impact": 5,
    "risk_score": 20,
    "reasoning": "High exposure due to lack of physical security controls.",
    "related_controls": ["7.1 Physical security perimeters", "8.24 Use of cryptography"]
  }
  ```

---

### Skill 4: `audit_codebase`
- **Purpose**: Runs static AppSec and code health audits on `backend/` and `src/` for SQL/RLS injection, auth leaks, uncaught async exceptions, and credentials.
- **Persona**: Senior AppSec & Lead Developer.
- **Invocation**:
  ```powershell
  # CLI Execution
  backend\venv\Scripts\python.exe backend\scripts\audit\code_auditor.py --dirs backend src
  
  # Or via Python
  result = adapter.audit_codebase(target_dirs=["backend", "src"])
  ```

---

## 4. Virtual Environment & Execution Rules

1. **Interpreter Path**:
   Always use the backend virtual environment:
   - Windows: `backend\venv\Scripts\python.exe`
   - Linux / CI: `backend/venv/bin/python`

2. **Environment Variables**:
   - `GEMINI_API_KEY`: API key for Google Gemini (enables `gemini-3.8-flash` generation).
   - `GEMINI_MODEL`: (Optional) Override generation model string (defaults to `gemini-3.8-flash`).

3. **Fallback Guarantee**:
   All adapter methods provide non-blocking local fallbacks (using local embeddings, BM25, and heuristics) whenever `GEMINI_API_KEY` is not present or when the remote API encounters network failure.
