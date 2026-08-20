"""
Data Residency Validator — Hard-Stop Startup Checks for DATA_RESIDENCY_MODE="strict".

Rules:
  1. If LLM_MODE == "cloud": RuntimeError — data leaves the perimeter.
  2. QDRANT_URL must resolve, and the resolved IP must be private/loopback.
       - Always attempt DNS resolution via socket.getaddrinfo().
       - If resolution FAILS: RuntimeError (fail closed — ambiguous = reject).
       - If resolution succeeds and ANY returned address is public: RuntimeError.
       - No shape-based bypass (no special treatment of no-dot hostnames).
  3. Threshold defaults: log a visible WARNING if the operator is running
     strict mode with untuned gate thresholds.

Call `validate_data_residency(settings)` once at startup, before any model loads.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
import urllib.parse
from typing import Optional

logger = logging.getLogger("grc.data_residency")

# Default threshold values defined in config — used for "still at default" warning
_DEFAULT_TOP1_THRESHOLD = 0.65
_DEFAULT_MARGIN_THRESHOLD = 0.10


class DataResidencyError(RuntimeError):
    """Hard startup failure — data residency constraint violated."""


def _is_private_or_loopback(ip_str: str) -> bool:
    """Return True if the IP is RFC1918 private, loopback, or link-local."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def _validate_qdrant_url(qdrant_url: str) -> None:
    """
    Validate that QDRANT_URL resolves exclusively to private/loopback addresses.

    Resolution logic:
      - Always call socket.getaddrinfo() — no shape-based shortcircuiting.
      - If getaddrinfo() raises: fail closed with RuntimeError.
      - If any resolved address is public: RuntimeError.
    """
    parsed = urllib.parse.urlparse(qdrant_url)
    hostname = parsed.hostname
    if not hostname:
        raise DataResidencyError(
            f"DATA_RESIDENCY_MODE=strict: QDRANT_URL '{qdrant_url}' has no parseable hostname."
        )

    logger.info(f"Data residency: Resolving QDRANT_URL hostname '{hostname}'...")

    try:
        # getaddrinfo returns list of (family, type, proto, canonname, sockaddr)
        # sockaddr is (address, port) for AF_INET or (address, port, flow, scope) for AF_INET6
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise DataResidencyError(
            f"DATA_RESIDENCY_MODE=strict: QDRANT_URL hostname '{hostname}' could not be resolved "
            f"({exc}). Unresolvable hostname is ambiguous — failing closed. "
            f"Fix the hostname or disable strict mode."
        ) from exc

    if not addr_infos:
        raise DataResidencyError(
            f"DATA_RESIDENCY_MODE=strict: QDRANT_URL hostname '{hostname}' returned no addresses."
        )

    # Collect all unique IPs from all address families
    resolved_ips = set()
    for family, _type, _proto, _canonname, sockaddr in addr_infos:
        # sockaddr[0] is the IP string for both IPv4 and IPv6
        resolved_ips.add(sockaddr[0])

    logger.info(f"Data residency: '{hostname}' resolved to {resolved_ips}")

    public_ips = [ip for ip in resolved_ips if not _is_private_or_loopback(ip)]
    if public_ips:
        raise DataResidencyError(
            f"DATA_RESIDENCY_MODE=strict: QDRANT_URL hostname '{hostname}' resolved to public "
            f"address(es) {public_ips}. Qdrant must be on a private/loopback address in strict mode. "
            f"Set QDRANT_URL to a local or private-network endpoint."
        )

    logger.info(
        f"Data residency: QDRANT_URL '{qdrant_url}' resolved to private/loopback addresses only — OK"
    )


def _validate_llm_mode(llm_mode: str) -> None:
    """Reject LLM_MODE='cloud' in strict mode — inference data must not leave the perimeter."""
    if llm_mode == "cloud":
        raise DataResidencyError(
            f"DATA_RESIDENCY_MODE=strict: LLM_MODE='{llm_mode}' sends inference data to an external "
            f"API. Set LLM_MODE to 'local-only' or 'self-hosted' to comply with strict data residency."
        )


def _warn_threshold_defaults(top1: float, margin: float) -> None:
    """
    Emit a visible WARNING if confidence gate thresholds are still at their
    untuned defaults. In strict mode the operator should have reviewed these.
    """
    if top1 == _DEFAULT_TOP1_THRESHOLD and margin == _DEFAULT_MARGIN_THRESHOLD:
        logger.warning(
            "DATA_RESIDENCY_MODE=strict: Confidence gate thresholds are still at their untuned "
            "defaults (top1=%.2f, margin=%.2f). In strict mode these should be evaluated against "
            "your organisation's document corpus before going to production.",
            top1,
            margin,
        )


def validate_data_residency(settings) -> None:
    """
    Entry point — call once at startup with the loaded Settings object.
    Performs all strict-mode checks in order. Any violation raises DataResidencyError,
    which the caller (main.py) should let propagate to abort startup.

    Does nothing if DATA_RESIDENCY_MODE != 'strict'.
    """
    mode = getattr(settings, "DATA_RESIDENCY_MODE", "off")
    if mode != "strict":
        logger.debug(f"Data residency: mode='{mode}' — strict checks skipped")
        return

    logger.info("Data residency: MODE=strict — running startup validation checks...")

    # 1. Hard block: LLM_MODE must not be cloud
    _validate_llm_mode(settings.LLM_MODE)

    # 2. Hard block: QDRANT_URL must resolve to a private/loopback address
    _validate_qdrant_url(settings.QDRANT_URL)

    # 3. Advisory warning: thresholds at default
    _warn_threshold_defaults(
        settings.CONFIDENCE_GATE_TOP1_THRESHOLD,
        settings.CONFIDENCE_GATE_MARGIN_THRESHOLD,
    )

    logger.info("Data residency: All strict-mode checks passed.")
