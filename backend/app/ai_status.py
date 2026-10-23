"""AI status probe, wake orchestration, and rate limiting."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.errors import RateLimitedError
from app.schemas import AiState, AiStatus, AiWakeResult


def _now() -> datetime:
    return datetime.now(timezone.utc)


def available_modes(state: AiState) -> list[str]:
    if state == "READY":
        return ["LLM", "FALLBACK", "ALIAS_ONLY"]
    return ["FALLBACK", "ALIAS_ONLY"]


class AiOrchestrator:
    """Small state machine around health and wake HTTP calls.

    The transport is injectable so tests can prove transitions without a real
    AI endpoint. The API key is sent only in the server-side Authorization
    header and never appears in a response.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
        wake_rate_limit_s: int | None = None,
        warmup_grace_s: int | None = None,
    ) -> None:
        self.settings = settings
        self.health_url = settings.ai_health_url or settings.ai_service_url
        self.wake_url = settings.ai_wake_url or settings.ai_service_url
        self.api_key = (
            settings.ai_api_key.get_secret_value() if settings.ai_api_key is not None else None
        )
        self.timeout_s = min(settings.ai_timeout_s, 2.5)
        self.wake_rate_limit_s = (
            wake_rate_limit_s if wake_rate_limit_s is not None else settings.ai_wake_rate_limit_s
        )
        self.warmup_grace_s = (
            warmup_grace_s if warmup_grace_s is not None else settings.ai_warmup_grace_s
        )
        self._client = client or httpx.Client(timeout=self.timeout_s)
        self._owns_client = client is None
        self._lock = threading.Lock()
        self._state: AiState = "DEGRADED" if self.health_url else "OFFLINE"
        self._message = (
            "AI endpoint configured; readiness has not been verified."
            if self.health_url
            else "AI endpoint not configured; local fallback/manual path only."
        )
        self._last_checked = time.monotonic()
        self._last_wake_at: float | None = None
        self._last_wake_user: str | None = None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _status(self, state: AiState, message: str) -> AiStatus:
        return AiStatus(
            state=state,
            available_modes=available_modes(state),  # type: ignore[arg-type]
            fallback_available=True,
            last_checked_at=_now(),
            message=message,
        )

    def _probe(self) -> tuple[AiState, str]:
        if not self.health_url:
            return "OFFLINE", "AI endpoint not configured; local fallback/manual path only."
        try:
            response = self._client.get(
                self.health_url,
                headers=self._headers(),
                timeout=self.timeout_s,
            )
        except httpx.HTTPError:
            return "OFFLINE", "AI health check could not connect; local fallback remains available."
        if 200 <= response.status_code < 300:
            return "READY", "AI health check passed; LLM inference may be available."
        if response.status_code in {401, 403}:
            return "DEGRADED", "AI endpoint rejected credentials; local fallback remains available."
        if response.status_code == 429:
            return "DEGRADED", "AI endpoint is rate limited; local fallback remains available."
        if response.status_code >= 500:
            return "DEGRADED", "AI endpoint is unhealthy; local fallback remains available."
        return "OFFLINE", "AI endpoint rejected the health probe; local fallback remains available."

    def status(self) -> AiStatus:
        with self._lock:
            if not self.health_url:
                self._state = "OFFLINE"
                self._message = "AI endpoint not configured; local fallback/manual path only."
                return self._status(self._state, self._message)
            now = time.monotonic()
            if (
                self._state == "WARMING"
                and self._last_wake_at is not None
                and now - self._last_wake_at < self.warmup_grace_s
            ):
                return self._status(
                    "WARMING",
                    "AI is warming up; local fallback remains available.",
                )
            state, message = self._probe()
            self._state = state
            self._message = message
            self._last_checked = now
            return self._status(state, message)

    def wake(self, user_id: str) -> AiWakeResult:
        if not self.wake_url:
            return AiWakeResult(
                state="OFFLINE",
                accepted=False,
                fallback_available=True,
                last_checked_at=_now(),
                message="AI endpoint not configured; no wake request was sent.",
            )
        with self._lock:
            now = time.monotonic()
            if (
                self._last_wake_user == user_id
                and self._last_wake_at is not None
                and now - self._last_wake_at < self.wake_rate_limit_s
            ):
                retry_after = max(
                    1,
                    int(self.wake_rate_limit_s - (now - self._last_wake_at)),
                )
                raise RateLimitedError(
                    details={
                        "scope": "AI_WAKE",
                        "retry_after_seconds": retry_after,
                    }
                )
            self._last_wake_at = now
            self._last_wake_user = user_id
            self._state = "WARMING"
            self._last_checked = now
            self._message = "AI wake request sent; waiting for readiness."
            try:
                response = self._client.post(
                    self.wake_url,
                    headers=self._headers(),
                    json={"wake": True},
                    timeout=self.timeout_s,
                )
            except httpx.HTTPError:
                self._state = "OFFLINE"
                self._message = (
                    "AI wake request could not connect; local fallback remains available."
                )
                return self._wake_result(False)
            if not 200 <= response.status_code < 300:
                self._state = "DEGRADED"
                self._message = (
                    f"AI wake request returned HTTP {response.status_code}; "
                    "local fallback remains available."
                )
                return self._wake_result(False)
            self._state = "WARMING"
            self._message = "AI wake request accepted; readiness is still warming."
            return self._wake_result(True)

    def _wake_result(self, accepted: bool) -> AiWakeResult:
        return AiWakeResult(
            state=self._state,
            accepted=accepted,
            fallback_available=True,
            last_checked_at=_now(),
            message=self._message,
        )
