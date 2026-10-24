"""Shared shape for executable verifier problem specifications."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Example:
    args: tuple[Any, ...]
    expected: Any


@dataclass(frozen=True)
class Spec:
    slug: str
    method: str
    # Complete Python source defining class Solution with ``method``.
    oracle_code: str
    # Source defining generate_cases(rng, count) -> list[tuple].
    gen_code: str
    # Source defining validate(args) -> bool.
    validate_code: str
    examples: tuple[Example, ...]
    # One LeetCode-valid-shaped argument tuple that violates a constraint.
    invalid_input: tuple[Any, ...]
