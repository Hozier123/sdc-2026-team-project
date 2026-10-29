"""Provider-aware readiness and single-flight background inference warmup."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from app.ai.prompt import build_system_prompt
from app.ai_runtime import AiRuntimeConfig, resolve_ai_runtime
from app.config import Settings
from app.errors import RateLimitedError
from app.extraction.ai import AiExtraction
from app.schemas import AiState, AiStatus, AiWakeResult

_PROBE_TEXT = "Milo 1 ctn"
_FALLBACK = " Local fallback/manual handling remains available."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def available_modes(state: AiState) -> list[str]:
    return ["LLM", "FALLBACK", "ALIAS_ONLY"] if state == "READY" else ["FALLBACK", "ALIAS_ONLY"]


class _ProbeFailure(Exception):
    def __init__(self, state: AiState, message: str):
        self.state = state
        self.message = message + _FALLBACK


class AiOrchestrator:
    """Health is reachability; READY additionally requires recent valid inference.

    Wake accepts one background job per process and never controls GPU workers.
    Inject an httpx MockTransport for GPU-free tests. The warmup_grace_s argument
    remains accepted for compatibility; job completion now determines WARMING.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        runtime: AiRuntimeConfig | None = None,
        client: httpx.Client | None = None,
        wake_rate_limit_s: int | None = None,
        warmup_grace_s: int | None = None,
    ) -> None:
        self.runtime = runtime or resolve_ai_runtime(settings)
        self._client = client or httpx.Client(timeout=self.runtime.probe_timeout_s)
        self._owns_client = client is None
        self._wake_rate_limit_s = (
            settings.ai_wake_rate_limit_s if wake_rate_limit_s is None else wake_rate_limit_s
        )
        self._readiness_ttl_s = settings.ai_readiness_ttl_s
        self._lock = threading.Lock()
        self._executor: ThreadPoolExecutor | None = None
        self._warmup: Future | None = None
        self._closed = False
        self._wake_users: dict[str, float] = {}
        self._last_inference_at: float | None = None
        self._revision = 0
        self._state: AiState = "OFFLINE" if self.runtime.provider == "stub" else "DEGRADED"
        self._message = (
            "Local provider selected; no model inference or wake is configured."
            if self.runtime.provider == "stub"
            else "AI provider configured; model inference has not been verified."
        ) + _FALLBACK

    def close(self) -> None:
        with self._lock:
            self._closed = True
            executor = self._executor
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
        if self._owns_client:
            self._client.close()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.runtime.api_key is not None:
            headers["Authorization"] = f"Bearer {self.runtime.api_key.get_secret_value()}"
        return headers

    def _request(
        self, method: str, url: str, *, deadline: float | None = None, **kwargs
    ) -> httpx.Response:
        timeout = self.runtime.probe_timeout_s
        if deadline is not None:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                raise _ProbeFailure("OFFLINE", "AI warmup timed out.")
        try:
            response = self._client.request(
                method, url, headers=self._headers(), timeout=timeout, **kwargs
            )
        except httpx.TimeoutException:
            raise _ProbeFailure("OFFLINE", "AI request timed out.") from None
        except httpx.HTTPError:
            raise _ProbeFailure("OFFLINE", "AI endpoint could not connect.") from None
        if not 200 <= response.status_code < 300:
            code = response.status_code
            if code in {401, 403}:
                raise _ProbeFailure("DEGRADED", "AI endpoint rejected credentials.")
            if code == 429:
                raise _ProbeFailure("DEGRADED", "AI endpoint is rate limited.")
            state: AiState = "DEGRADED" if code >= 500 else "OFFLINE"
            raise _ProbeFailure(state, f"AI endpoint returned HTTP {code}.")
        return response

    def _check_service(self, deadline: float | None = None) -> None:
        if self.runtime.health_url:
            self._request("GET", self.runtime.health_url, deadline=deadline)
        if self.runtime.models_url:
            response = self._request("GET", self.runtime.models_url, deadline=deadline)
            try:
                models = response.json()["data"]
                matched = any(model["id"] == self.runtime.model_name for model in models)
            except (ValueError, KeyError, TypeError):
                raise _ProbeFailure("DEGRADED", "AI model listing is invalid.") from None
            if not matched:
                raise _ProbeFailure("DEGRADED", "Configured AI model is not served.")

    def _verify_inference(self, deadline: float) -> None:
        if self.runtime.provider == "runpod_adapter":
            payload = {
                "model": self.runtime.model_name,
                "messages": [
                    {"role": "system", "content": build_system_prompt(["FAM_MILO"])},
                    {"role": "user", "content": _PROBE_TEXT},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
                "max_tokens": 256,
            }
        else:
            payload = {
                "masked_text": _PROBE_TEXT,
                "language_hint": "en",
                "request_id": f"ai-warmup-{uuid4().hex}",
            }
        response = self._request(
            "POST", self.runtime.inference_url, deadline=deadline, json=payload
        )
        try:
            data = response.json()
            if self.runtime.provider == "runpod_adapter":
                if data.get("model", self.runtime.model_name) != self.runtime.model_name:
                    raise ValueError("model mismatch")
                data = json.loads(data["choices"][0]["message"]["content"])
                # The model also uses an empty string for an absent optional
                # pack size. Production extraction treats it as absent.
                if isinstance(data, dict) and isinstance(data.get("rows"), list):
                    data = {
                        **data,
                        "rows": [
                            {**row, "pack_size": None}
                            if isinstance(row, dict) and row.get("pack_size") == ""
                            else row
                            for row in data["rows"]
                        ],
                    }
            result = AiExtraction.model_validate(data)
            if len(result.rows) != 1 or result.ignored_spans:
                raise ValueError("invalid probe result")
            row = result.rows[0]
            if (
                row.span != _PROBE_TEXT
                or row.fam != "FAM_MILO"
                or row.qty != 1
                or row.uom != "ctn"
                or row.pack_size is not None
                or row.conds
            ):
                raise ValueError("unexpected probe extraction")
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise _ProbeFailure(
                "DEGRADED", "AI returned an invalid inference probe result."
            ) from None

    def _run_warmup(self, revision: int) -> None:
        try:
            deadline = time.monotonic() + self.runtime.warmup_timeout_s
            # An explicit legacy wake hook may be what starts its HTTP service.
            if self.runtime.provider == "http" and self.runtime.wake_url:
                self._request("POST", self.runtime.wake_url, deadline=deadline, json={"wake": True})
            self._check_service(deadline)
            self._verify_inference(deadline)
            state: AiState = "READY"
            message = "AI model verified by a valid synthetic extraction."
        except _ProbeFailure as exc:
            state, message = exc.state, exc.message
        except Exception:
            state, message = "DEGRADED", "AI warmup verification failed." + _FALLBACK
        with self._lock:
            # A newer real parse result takes precedence over an older warmup.
            if self._closed or revision != self._revision:
                return
            self._state, self._message = state, message
            self._last_inference_at = time.monotonic() if state == "READY" else None

    def observe_inference(self, mode: str | None) -> None:
        """Record only actual provider calls, never customer-memory bypasses."""
        with self._lock:
            if self.runtime.provider == "stub" or self._closed or mode == "ALIAS_ONLY":
                return
            self._revision += 1
            if mode == "LLM":
                self._last_inference_at = time.monotonic()
                self._state = "READY"
                self._message = "The latest provider extraction succeeded."
            else:
                self._last_inference_at = None
                self._state = "DEGRADED"
                self._message = "The latest extraction did not verify LLM inference." + _FALLBACK

    def _status(self) -> AiStatus:
        return AiStatus(
            state=self._state,
            available_modes=available_modes(self._state),  # type: ignore[arg-type]
            fallback_available=True,
            last_checked_at=_now(),
            message=self._message,
        )

    def status(self) -> AiStatus:
        with self._lock:
            if self.runtime.provider == "stub" or self._closed:
                return self._status()
            if self._warmup is not None and not self._warmup.done():
                return self._status()
            try:
                self._check_service()
            except _ProbeFailure as exc:
                self._last_inference_at = None
                self._state, self._message = exc.state, exc.message
                return self._status()
            if (
                self._last_inference_at is not None
                and time.monotonic() - self._last_inference_at < self._readiness_ttl_s
            ):
                self._state = "READY"
            else:
                expired = self._last_inference_at is not None or self._state == "OFFLINE"
                self._state = "DEGRADED"
                if expired:
                    self._message = (
                        "AI inference is unverified or expired; use Wake AI "
                        "or ask the team to warm up." + _FALLBACK
                    )
            return self._status()

    def _wake_result(self, accepted: bool) -> AiWakeResult:
        return AiWakeResult(
            **self._status().model_dump(exclude={"available_modes"}), accepted=accepted
        )

    def wake(self, user_id: str) -> AiWakeResult:
        with self._lock:
            if self.runtime.provider == "stub" or self._closed:
                return self._wake_result(False)
            now = time.monotonic()
            self._wake_users = {
                user: at
                for user, at in self._wake_users.items()
                if now - at < self._wake_rate_limit_s
            }
            if user_id in self._wake_users:
                raise RateLimitedError(
                    details={
                        "scope": "AI_WAKE",
                        "retry_after_seconds": max(
                            1, int(self._wake_rate_limit_s - (now - self._wake_users[user_id]))
                        ),
                    }
                )
            self._wake_users[user_id] = now
            if self._warmup is not None and not self._warmup.done():
                return self._wake_result(True)
            self._revision += 1
            self._last_inference_at = None
            self._state = "WARMING"
            self._message = "Background inference verification accepted; readiness is pending."
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ai-warmup")
            self._warmup = self._executor.submit(self._run_warmup, self._revision)
            return self._wake_result(True)
