"""Small deterministic shrinkers used only after a mismatch is found."""

from __future__ import annotations

from collections.abc import Callable

from app.services.counterexamples.oracles import TwoSumAdapter

TwoSumMismatch = Callable[[dict[str, object]], bool]


def shrink_two_sum(
    input_data: dict[str, object], still_mismatches: TwoSumMismatch
) -> dict[str, object]:
    """Greedily remove values and reduce magnitudes while retaining a mismatch."""
    adapter = TwoSumAdapter()
    nums, target = adapter.decode_input(input_data)
    best = adapter.encode_input(list(nums), target)

    changed = True
    while changed:
        changed = False
        current_nums, _ = adapter.decode_input(best)
        for index in range(len(current_nums)):
            if len(current_nums) <= 2:
                break
            candidate = adapter.encode_input(
                current_nums[:index] + current_nums[index + 1 :], target
            )
            if still_mismatches(candidate):
                best = candidate
                changed = True
                break

    current_nums, _ = adapter.decode_input(best)
    for index, value in enumerate(current_nums):
        for replacement in _smaller_values(value):
            candidate_nums = list(current_nums)
            candidate_nums[index] = replacement
            candidate = adapter.encode_input(candidate_nums, target)
            if still_mismatches(candidate):
                best = candidate
                current_nums = candidate_nums
                break
    return best


def _smaller_values(value: int) -> tuple[int, ...]:
    candidates = (0, value // 2, -1 if value < 0 else 1)
    return tuple(candidate for candidate in candidates if candidate != value)
