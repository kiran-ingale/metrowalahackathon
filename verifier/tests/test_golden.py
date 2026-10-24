from __future__ import annotations

import json
from pathlib import Path

import pytest

from verifier.app.orchestrator import run_counterexample


ROOT = Path(__file__).resolve().parents[2]
SLUGS = (
    "coin_change",
    "house_robber",
    "maximum_subarray",
    "jump_game",
    "longest_increasing_subsequence",
)


@pytest.mark.parametrize("slug", SLUGS)
def test_golden_wrong_and_correct_candidates(slug: str) -> None:
    golden = json.loads(
        (ROOT / "verifier" / "golden" / f"{slug}.json").read_text(encoding="utf-8")
    )

    wrong = run_counterexample(slug, golden["wrong_code"])
    assert wrong.status == "found"
    assert wrong.trust_label == "verified_counterexample"
    assert wrong.reproduced is True
    assert wrong.minimized is True
    assert wrong.input is not None
    list_sizes = [len(value) for value in wrong.input.values() if isinstance(value, list)]
    assert max(list_sizes, default=0) <= 6

    correct = run_counterexample(slug, golden["correct_code"])
    assert correct.status == "no_mismatch"
    assert correct.tests_run == 200
    assert correct.message == "No counterexample found in 200 tests."




def test_missing_adapter_is_not_supported() -> None:
    result = run_counterexample("not-a-leetcode-adapter", "")
    assert result.status == "not_supported"
    assert result.trust_label == "could_not_verify"
