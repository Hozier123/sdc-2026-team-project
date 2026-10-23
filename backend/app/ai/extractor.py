"""Asynchronous RunPod Serverless extraction client with offline fallback resilience.

Complies strictly with Gate 0 v4 contract and Review Revision v2:
- 4000 Unicode code points physical hard limit (throws MessageTooLongError -> 422)
- Typed exceptions: MessageTooLongError (422), AiAndFallbackUnavailableError (503)
- Strict positive integer quantity sanitation: 1..999999, ASCII digits only, rejects bool/0/negative
- LlmRow complies with v1.3 §2.1 (span, fam, qty, uom, pack_size, conds)
- Resilience fallback: automatically degrades to fallback.py on timeout or error
- Zero false draft: if fallback fails due to missing lexicon, raises AiAndFallbackUnavailableError (503)
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import httpx

from app.ai.fallback import DEFAULT_SEED_CATALOG, FallbackLine, extract_fallback_order
from app.ai.prompt import LlmExtractionResult, LlmRow, build_system_prompt

logger = logging.getLogger(__name__)

# Constants
MAX_MESSAGE_CODE_POINTS: int = 4000
DEFAULT_TIMEOUT_S: float = 8.0
MAX_OUTPUT_TOKENS: int = 2048


class MessageTooLongError(ValueError):
    """Raised when input text exceeds 4000 Unicode code points (maps to HTTP 422)."""

    pass


class AiAndFallbackUnavailableError(RuntimeError):
    """Raised when both LLM and Fallback are unavailable (maps to HTTP 503)."""

    pass


@dataclass(frozen=True)
class ExtractorResponse:
    """Standardized response from the AI extraction subsystem."""

    result: LlmExtractionResult
    ai_mode: str  # "LLM" or "FALLBACK"
    latency_ms: float
    raw_error: Optional[str] = None


def _sanitize_qty(qty_val: Any) -> Optional[int]:
    """Strictly sanitize quantity per H1 and v1.3 §2.1.

    Rules:
    - Boolean values (e.g. True) MUST be rejected (Python bool is subclass of int!)
    - Strings must be pure ASCII digits: isascii() and isdigit()
    - Integers must be strictly positive in range 1..999999 (0 and negatives rejected)
    """
    if isinstance(qty_val, bool):
        return None

    if isinstance(qty_val, str):
        qty_str = qty_val.strip()
        if qty_str.isascii() and qty_str.isdigit():
            qty_int = int(qty_str)
            if 1 <= qty_int <= 999999:
                return qty_int
        return None

    if isinstance(qty_val, int):
        if 1 <= qty_val <= 999999:
            return qty_val
        return None

    return None


class RunPodExtractor:
    """Asynchronous client for RunPod Serverless with deterministic Fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        timeout_s: Optional[float] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("RUNPOD_API_KEY", "")
        self.endpoint_id = endpoint_id or os.getenv("RUNPOD_ENDPOINT_ID", "")
        self.timeout_s = timeout_s or float(os.getenv("LLM_TIMEOUT_S", str(DEFAULT_TIMEOUT_S)))
        self.model_name = model_name or os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct-AWQ")

        if base_url:
            self.api_url = base_url
        elif self.endpoint_id:
            self.api_url = f"https://{self.endpoint_id}.api.runpod.ai/v1/chat/completions"
        else:
            self.api_url = ""

    async def probe_version(self) -> Dict[str, Any]:
        """Probe RunPod /v1/version endpoint for readiness check.

        Returns:
            JSON response from /v1/version or empty dict if unreachable.
        """
        if not self.endpoint_id:
            return {}
        version_url = f"https://{self.endpoint_id}.api.runpod.ai/v1/version"
        headers: Dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.get(version_url, headers=headers)
                if resp.status_code == 200:
                    return resp.json()
                return {}
        except Exception as err:
            logger.warning("RunPod probe_version failed: %s", err)
            return {}

    async def extract(
        self,
        masked_text: str,
        catalog: Optional[Dict[str, Sequence[str]]] = None,
    ) -> ExtractorResponse:
        """Extract product lines and conditions from masked message.

        Args:
            masked_text: Input message with PII already redacted.
            catalog: Allowed product family whitelist mapping.

        Returns:
            ExtractorResponse containing LlmExtractionResult and ai_mode.

        Raises:
            MessageTooLongError: If masked_text exceeds 4000 Unicode code points (HTTP 422).
            AiAndFallbackUnavailableError: If both LLM and Fallback are unavailable (HTTP 503).
        """
        code_point_len = len(masked_text)
        if code_point_len > MAX_MESSAGE_CODE_POINTS:
            raise MessageTooLongError(
                f"Message length ({code_point_len} code points) exceeds physical limit of {MAX_MESSAGE_CODE_POINTS}."
            )

        if catalog is None:
            catalog = DEFAULT_SEED_CATALOG

        family_ids = list(catalog.keys())

        # If no RunPod credentials configured, directly use fallback protected by try/except
        if not self.api_key or not self.api_url:
            try:
                return self._execute_fallback(
                    masked_text,
                    catalog,
                    reason="No RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID configured.",
                )
            except Exception as fb_err:
                logger.critical("Offline fallback failed: %s", str(fb_err))
                if isinstance(fb_err, AiAndFallbackUnavailableError):
                    raise fb_err
                raise AiAndFallbackUnavailableError(str(fb_err)) from fb_err

        system_prompt = build_system_prompt(family_ids)
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": masked_text},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
            "max_tokens": MAX_OUTPUT_TOKENS,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(self.api_url, json=payload, headers=headers)
                elapsed_ms = (time.time() - start_time) * 1000.0

                if resp.status_code != 200:
                    logger.warning(
                        "RunPod returned non-200 status %d: %s. Degrading to fallback.",
                        resp.status_code,
                        resp.text,
                    )
                    return self._execute_fallback(
                        masked_text,
                        catalog,
                        reason=f"RunPod HTTP {resp.status_code}",
                        latency_ms=elapsed_ms,
                    )

                data = resp.json()
                raw_content = data["choices"][0]["message"]["content"]
                parsed_json = json.loads(raw_content)

                validated_result = self._validate_and_sanitize(parsed_json, family_ids)
                return ExtractorResponse(
                    result=validated_result,
                    ai_mode="LLM",
                    latency_ms=elapsed_ms,
                    raw_error=None,
                )

        except (httpx.TimeoutException, httpx.RequestError) as net_err:
            elapsed_ms = (time.time() - start_time) * 1000.0
            logger.warning(
                "RunPod request failed/timed out after %.1fms (%s). Gracefully degrading to fallback.",
                elapsed_ms,
                str(net_err),
            )
            return self._execute_fallback(
                masked_text,
                catalog,
                reason=f"Network/Timeout error: {type(net_err).__name__}",
                latency_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000.0
            logger.error("Unexpected error in LLM extraction: %s. Degrading to fallback.", str(exc))
            return self._execute_fallback(
                masked_text,
                catalog,
                reason=f"Extraction exception: {str(exc)}",
                latency_ms=elapsed_ms,
            )

    def _validate_and_sanitize(
        self,
        raw_data: Dict[str, Any],
        family_whitelist: Sequence[str],
    ) -> LlmExtractionResult:
        """Validate LLM output, sanitize quantity, and isolate faults per row."""
        raw_rows = raw_data.get("rows", [])
        sanitized_rows: List[LlmRow] = []

        for item in raw_rows:
            try:
                span = str(item.get("span", "")).strip()
                fam = str(item.get("fam", "")).strip()

                if not fam or fam not in family_whitelist:
                    fam = "UNKNOWN"

                qty_val = _sanitize_qty(item.get("qty"))

                conds_val = item.get("conds", [])
                if not isinstance(conds_val, list):
                    conds_val = []

                sanitized_rows.append(
                    LlmRow(
                        span=span,
                        fam=fam,
                        qty=qty_val,
                        uom=item.get("uom"),
                        pack_size=item.get("pack_size"),
                        conds=[str(c) for c in conds_val],
                    )
                )
            except Exception as row_err:
                logger.debug("Row sanitization degraded row to UNKNOWN: %s", row_err)
                sanitized_rows.append(
                    LlmRow(
                        span=str(item.get("span", "UNKNOWN")),
                        fam="UNKNOWN",
                        qty=None,
                        uom=None,
                        pack_size=None,
                        conds=[],
                    )
                )

        ignored = [str(s) for s in raw_data.get("ignored_spans", [])]
        return LlmExtractionResult(rows=sanitized_rows, ignored_spans=ignored)

    def _execute_fallback(
        self,
        masked_text: str,
        catalog: Dict[str, Sequence[str]],
        reason: str,
        latency_ms: float = 0.0,
    ) -> ExtractorResponse:
        """Degrade to deterministic RapidFuzz fallback engine."""
        try:
            fallback_lines: List[FallbackLine] = extract_fallback_order(
                masked_text, catalog=catalog
            )
        except Exception as fb_err:
            raise AiAndFallbackUnavailableError(str(fb_err)) from fb_err

        rows: List[LlmRow] = []
        for f_line in fallback_lines:
            rows.append(
                LlmRow(
                    span=f_line.span,
                    fam=f_line.family_id,
                    qty=f_line.qty,
                    uom=f_line.uom,
                    pack_size=f_line.pack_size,
                    conds=[],
                )
            )

        return ExtractorResponse(
            result=LlmExtractionResult(rows=rows, ignored_spans=[]),
            ai_mode="FALLBACK",
            latency_ms=latency_ms,
            raw_error=reason,
        )
