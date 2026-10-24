"""Deterministic bounded input generators for trusted adapters."""

from __future__ import annotations

from random import Random

from app.services.counterexamples.oracles import TwoSumAdapter

DEFAULT_SEED = 20261024
DEFAULT_CASE_LIMIT = 32


def generate_two_sum_cases(
    seed: int = DEFAULT_SEED, case_limit: int = DEFAULT_CASE_LIMIT
) -> list[dict[str, object]]:
    """Return a stable mix of edge cases and small pseudo-random cases."""
    if case_limit < 1 or case_limit > 100:
        raise ValueError("case_limit must be between 1 and 100.")

    adapter = TwoSumAdapter()
    cases = [
        adapter.encode_input([1, 2, 3], 6),
        adapter.encode_input([3, 3], 6),
        adapter.encode_input([-1, 0, 1], 0),
        adapter.encode_input([1, 2, 4], 8),
    ]
    random = Random(seed)
    while len(cases) < case_limit:
        length = random.randint(2, 6)
        nums = [random.randint(-8, 8) for _ in range(length)]
        if random.randrange(2):
            first_index, second_index = sorted(random.sample(range(length), 2))
            target = nums[first_index] + nums[second_index]
        else:
            target = random.randint(-16, 16)
        cases.append(adapter.encode_input(nums, target))
    return cases[:case_limit]
