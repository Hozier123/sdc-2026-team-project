"""Unit tests for the manual six-sample AI evidence runner."""

import asyncio

from app.ai.adapter import AdapterOutput
from app.config import REPO_ROOT
from tools.run_ai_samples import load_samples, run_samples, summarize


class FakeAdapter:
    def __init__(self, mode: str = "LLM", fail: bool = False) -> None:
        self.mode = mode
        self.fail = fail
        self.calls: list[tuple[str, dict]] = []

    async def adapt(self, masked_text, catalog):
        self.calls.append((masked_text, catalog))
        if self.fail:
            raise RuntimeError("endpoint unavailable")
        return AdapterOutput(lines=[], conditions=[], ai_mode=self.mode, ignored_spans=[])


def _samples() -> list[dict]:
    return [
        {
            "_sample_name": "normal",
            "input": {"masked_text": "Tepung 5 ctn", "request_id": "req-1"},
            "expected_response": {"rows": [], "ignored_spans": []},
        },
        {
            "_sample_name": "empty",
            "input": {"masked_text": "terima kasih", "request_id": "req-2"},
            "expected_response": {"rows": [], "ignored_spans": ["terima kasih"]},
        },
    ]


def test_load_samples_returns_exactly_six_canonical_files():
    samples = load_samples(REPO_ROOT / "docs" / "ai_contract" / "samples")
    assert [sample["_sample_name"] for sample in samples] == [
        "normal",
        "ambiguous",
        "condition",
        "empty",
        "multi_candidate",
        "multi_line",
    ]


def test_run_samples_preserves_request_actual_and_summary():
    catalog = {"FAM_TEPUNG": ["Tepung"]}
    fake = FakeAdapter(mode="LLM")
    results = asyncio.run(run_samples(fake, _samples(), catalog))

    assert results[0]["sample"] == "normal"
    assert results[0]["request_id"] == "req-1"
    assert results[0]["actual"]["ai_mode"] == "LLM"
    assert results[0]["error"] is None
    assert fake.calls == [
        ("Tepung 5 ctn", catalog),
        ("terima kasih", catalog),
    ]
    assert summarize(results) == {
        "total": 2,
        "llm": 2,
        "fallback": 0,
        "mixed": 0,
        "alias_only": 0,
        "errors": 0,
    }


def test_fallback_and_error_are_not_treated_as_success():
    fallback = asyncio.run(run_samples(FakeAdapter(mode="FALLBACK"), _samples(), {}))
    assert summarize(fallback)["fallback"] == 2
    assert summarize(fallback)["llm"] == 0

    failed = asyncio.run(run_samples(FakeAdapter(fail=True), _samples(), {}))
    assert summarize(failed)["errors"] == 2
    assert all("endpoint unavailable" in result["error"] for result in failed)
