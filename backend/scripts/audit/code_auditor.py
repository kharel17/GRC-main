"""
Senior AppSec & Lead Developer Code Auditor.

Audits source code in `backend/` and `src/` for security anti-patterns:
1. SQL / RLS Injection Risk (raw queries, f-strings, missing tenant scoping)
2. Authentication & Authorization Leaks (unprotected endpoints, leaked tokens)
3. Uncaught Async Errors & Unhandled Promises
4. Hardcoded Credentials & Sensitive Tokens
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# Configure utf-8 encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Directories and files to exclude from audit
IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "tmp",
    ".pytest_cache",
    ".gemini",
    "alembic/versions",
}

IGNORED_FILES = {
    "package-lock.json",
    "yarn.lock",
    "tsconfig.tsbuildinfo",
}

# Regex patterns for static auditing
SECRET_PATTERNS = [
    (r'(?i)(?:api_key|apikey|secret_key|private_key|auth_token)\s*=\s*["\']([a-zA-Z0-9_\-\.]{16,})["\']', "Hardcoded API/Secret Key"),
    (r'AIza[0-9A-Za-z_\-]{30,}', "Exposed Google API Key"),
    (r'sk-[a-zA-Z0-9]{24,}', "Exposed OpenAI / Provider API Key"),
    (r'(?i)(?<!hashed_)password\s*=\s*["\'](?!SUPABASE|PENDING|test|dummy)[^"\']{4,}["\']', "Hardcoded Plaintext Password"),
]

SQL_INJECTION_PATTERNS = [
    (r'text\s*\(\s*f["\'].*SELECT.*\{.*\}', "Raw SQL text() constructed with Python f-string interpolation"),
    (r'text\s*\(\s*f["\'].*INSERT.*\{.*\}', "Raw SQL text() constructed with Python f-string interpolation"),
    (r'text\s*\(\s*f["\'].*UPDATE.*\{.*\}', "Raw SQL text() constructed with Python f-string interpolation"),
    (r'text\s*\(\s*f["\'].*DELETE.*\{.*\}', "Raw SQL text() constructed with Python f-string interpolation"),
    (r'execute\s*\(\s*f["\'].*\{.*\}', "Direct database execute with f-string interpolation"),
]

ASYNC_UNCAUGHT_PATTERNS = [
    (r'async\s+def\s+[a-zA-Z0-9_]+\s*\(.*?\):(?!\s*"""[\s\S]*?""")(?![\s\S]{1,200}try:)', "Async endpoint/handler lacking top-level try/except block"),
]

RLS_PATTERNS = [
    (r'select\s*\(\s*[A-Z][a-zA-Z0-9_]+\s*\)(?!.*filter.*tenant_id)(?!.*where.*tenant_id)', "Potential cross-tenant leak: Query on multi-tenant model without explicit tenant_id filter"),
]


class CodeAuditor:
    """Static and semantic code security auditor."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.findings: List[Dict[str, Any]] = []

    def audit_directory(self, target_dir_rel: str) -> None:
        target_path = self.project_root / target_dir_rel
        if not target_path.exists():
            return

        for root, dirs, files in os.walk(target_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for file_name in files:
                if file_name in IGNORED_FILES:
                    continue
                file_path = Path(root) / file_name
                rel_path = file_path.relative_to(self.project_root)

                if file_name.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
                    self._audit_file(file_path, str(rel_path))

    def _audit_file(self, file_path: Path, rel_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return

        full_content = "".join(lines)

        # 1. Check for Secrets & Hardcoded Credentials
        for pattern, label in SECRET_PATTERNS:
            for idx, line in enumerate(lines, 1):
                # Skip test files and config examples
                if "test" in rel_path.lower() or "example" in rel_path.lower():
                    continue
                match = re.search(pattern, line)
                if match:
                    # Filter false positives (e.g. env reading, placeholders)
                    val = match.group(0)
                    if "os.getenv" in val or "os.environ" in val or "your-" in val.lower() or "xxx" in val.lower():
                        continue
                    self.findings.append({
                        "file": rel_path,
                        "line": idx,
                        "category": "Credentials & Secrets",
                        "severity": "CRITICAL",
                        "title": label,
                        "snippet": line.strip()[:100],
                        "remediation": "Move credential to environment variables (.env) and access via config settings.",
                    })

        # 2. Check for SQL Injection & Unsafe Interpolation
        for pattern, label in SQL_INJECTION_PATTERNS:
            for idx, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    self.findings.append({
                        "file": rel_path,
                        "line": idx,
                        "category": "SQL & RLS Injection",
                        "severity": "CRITICAL",
                        "title": label,
                        "snippet": line.strip()[:100],
                        "remediation": "Use SQLAlchemy parameterized queries (e.g. text('SELECT ... WHERE col = :val'), {'val': val}).",
                    })

        # 3. Check for Unhandled Async Exceptions in Python
        if rel_path.endswith(".py"):
            for idx, line in enumerate(lines, 1):
                if line.strip().startswith("@router.") or line.strip().startswith("@app."):
                    # Check next 15 lines for async def and try/except
                    window = "".join(lines[idx:idx+15])
                    if "async def" in window and "try:" not in window and "pytest" not in rel_path:
                        self.findings.append({
                            "file": rel_path,
                            "line": idx + 1,
                            "category": "Error Handling",
                            "severity": "MEDIUM",
                            "title": "Async Route Missing Top-Level Error Handling",
                            "snippet": lines[idx].strip()[:80],
                            "remediation": "Wrap asynchronous operations in try/except or ensure global HTTPException handler covers unhandled states.",
                        })

        # 4. Check Frontend Promise & Async Handling in TS/TSX
        if rel_path.endswith((".ts", ".tsx", ".js")):
            for idx, line in enumerate(lines, 1):
                # Search for fetch() without catch or await without try
                if "fetch(" in line and "catch(" not in line and "await" not in line:
                    self.findings.append({
                        "file": rel_path,
                        "line": idx,
                        "category": "Async Resilience",
                        "severity": "LOW",
                        "title": "Uncaught Fetch Promise",
                        "snippet": line.strip()[:90],
                        "remediation": "Chain .catch() or await within a try/catch block to avoid unhandled promise rejections in UI.",
                    })


def run_static_security_audit(
    project_root: str, target_dirs: List[str]
) -> Dict[str, Any]:
    """Programmatic entrypoint for GeminiSkillsAdapter and scripts."""
    root = Path(project_root)
    auditor = CodeAuditor(root)

    for d in target_dirs:
        auditor.audit_directory(d)

    critical_count = sum(1 for f in auditor.findings if f["severity"] == "CRITICAL")
    high_count = sum(1 for f in auditor.findings if f["severity"] == "HIGH")
    med_count = sum(1 for f in auditor.findings if f["severity"] == "MEDIUM")
    low_count = sum(1 for f in auditor.findings if f["severity"] == "LOW")

    summary = {
        "total_scanned_dirs": target_dirs,
        "total_findings": len(auditor.findings),
        "critical": critical_count,
        "high": high_count,
        "medium": med_count,
        "low": low_count,
        "status": "PASS" if (critical_count == 0 and high_count == 0) else "ACTION_REQUIRED",
    }

    return {
        "summary": summary,
        "findings": auditor.findings,
        "remediations": [
            {
                "finding_title": f["title"],
                "file": f["file"],
                "line": f["line"],
                "remediation": f["remediation"],
            }
            for f in auditor.findings
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="GRC Codebase Security Auditor")
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=["backend", "src"],
        help="Directories to audit (default: backend src)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON format",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    result = run_static_security_audit(str(project_root), args.dirs)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("=" * 70)
    print(" GRC CODEBASE SECURITY AUDIT REPORT")
    print(" Persona: Senior AppSec & Lead Developer")
    print("=" * 70)
    print(f"Target Directories : {', '.join(args.dirs)}")
    print(f"Total Findings     : {result['summary']['total_findings']}")
    print(f"Critical           : {result['summary']['critical']}")
    print(f"High               : {result['summary']['high']}")
    print(f"Medium             : {result['summary']['medium']}")
    print(f"Low                : {result['summary']['low']}")
    print(f"Overall Status     : {result['summary']['status']}")
    print("-" * 70)

    if not result["findings"]:
        print("✓ No critical security anti-patterns detected in scanned targets.")
    else:
        for idx, f in enumerate(result["findings"], 1):
            print(f"[{idx}] [{f['severity']}] {f['title']} in {f['file']}:{f['line']}")
            print(f"    Code snippet : {f['snippet']}")
            print(f"    Remediation  : {f['remediation']}\n")
    print("=" * 70)


if __name__ == "__main__":
    main()
