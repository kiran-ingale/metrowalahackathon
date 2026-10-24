"""Compare ordered outcomes produced by the verifier sandboxes."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any


_OUTCOME_KEYS = ("err", "timeout", "skipped", "output_too_large")


def _numeric_close(left: int | float, right: int | float) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
    except OverflowError:
        return left == right


def _same_value(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(
            right, (int, float)
        ) and not isinstance(right, bool):
            return _numeric_close(left, right)
        return False
    if isinstance(left, float):
        return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_value(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, tuple):
        return len(left) == len(right) and all(
            _same_value(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, Mapping):
        return left.keys() == right.keys() and all(
            _same_value(left[key], right[key]) for key in left
        )
    return left == right


def _unpack(outcome: Any) -> tuple[str, Any]:
    if not isinstance(outcome, Mapping):
        return "err", f"Invalid sandbox outcome: {outcome!r}"
    if "ok" in outcome:
        return "ok", outcome["ok"]
    for key in _OUTCOME_KEYS:
        if key in outcome:
            return key, outcome[key]
    return "err", outcome.get("err", "Invalid sandbox outcome")


def compare(
    oracle_results: Sequence[Mapping[str, Any]],
    candidate_results: Sequence[Mapping[str, Any]],
    normalize: Callable[[Any], Any] | None = None,
) -> dict[str, Any] | None:
    """Return the first differing input outcome, or ``None`` when they agree.

    Successful values may be normalized before comparison. Floats use
    ``math.isclose`` (including when nested in lists or dictionaries). Outcome
    kinds remain distinct: a wrong value, an exception, a timeout, and excessive
    output are never collapsed into the same comparison result.
    """
    total = max(len(oracle_results), len(candidate_results))
    for index in range(total):
        if index >= len(oracle_results):
            return {
                "index": index,
                "kind": "extra_result",
                "expected": None,
                "got": candidate_results[index],
            }
        if index >= len(candidate_results):
            return {
                "index": index,
                "kind": "missing_result",
                "expected": oracle_results[index],
                "got": None,
            }

        oracle_kind, expected = _unpack(oracle_results[index])
        candidate_kind, got = _unpack(candidate_results[index])
        if oracle_kind != "ok":
            return {
                "index": index,
                "kind": f"oracle_{oracle_kind}",
                "expected": expected,
                "got": got if candidate_kind == "ok" else candidate_results[index],
            }
        if candidate_kind != "ok":
            return {
                "index": index,
                "kind": candidate_kind,
                "expected": expected,
                "got": got,
            }

        compared_expected = normalize(expected) if normalize is not None else expected
        compared_got = normalize(got) if normalize is not None else got
        if not _same_value(compared_expected, compared_got):
            return {
                "index": index,
                "kind": "wrong_output",
                "expected": expected,
                "got": got,
            }
    return None
