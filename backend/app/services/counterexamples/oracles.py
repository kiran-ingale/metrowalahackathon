"""Hand-authored, independently verified problem oracles."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class TwoSumAdapter:
    """Two Sum contract using sorted index pairs and ``None`` when no pair exists."""

    slug: str = "two-sum"

    @property
    def official_examples(self) -> tuple[tuple[dict[str, object], list[int] | None], ...]:
        return (
            ({"nums": [2, 7, 11, 15], "target": 9}, [0, 1]),
            ({"nums": [3, 2, 4], "target": 6}, [1, 2]),
            ({"nums": [3, 3], "target": 6}, [0, 1]),
            ({"nums": [1, 2, 3], "target": 7}, None),
        )

    def decode_input(self, input_data: object) -> tuple[list[int], int]:
        if not isinstance(input_data, Mapping):
            raise ValueError("Two Sum input must be an object.")
        nums = input_data.get("nums")
        target = input_data.get("target")
        if (
            not isinstance(nums, list)
            or len(nums) < 2
            or not all(isinstance(value, int) and not isinstance(value, bool) for value in nums)
            or not isinstance(target, int)
            or isinstance(target, bool)
        ):
            raise ValueError("Two Sum input must contain integer nums and an integer target.")
        return nums, target

    def oracle(self, input_data: object) -> list[int] | None:
        nums, target = self.decode_input(input_data)
        for first_index, first_value in enumerate(nums):
            for second_index in range(first_index + 1, len(nums)):
                if first_value + nums[second_index] == target:
                    return [first_index, second_index]
        return None

    def normalize_output(self, input_data: object, output: object) -> list[int] | None:
        nums, target = self.decode_input(input_data)
        if output is None:
            return None
        if (
            not isinstance(output, list)
            or len(output) != 2
            or not all(isinstance(index, int) and not isinstance(index, bool) for index in output)
        ):
            return None
        first_index, second_index = sorted(output)
        if (
            first_index == second_index
            or first_index < 0
            or second_index >= len(nums)
            or nums[first_index] + nums[second_index] != target
        ):
            return None
        return [first_index, second_index]

    def outputs_match(self, input_data: object, expected: object, actual: object) -> bool:
        normalized_actual = self.normalize_output(input_data, actual)
        if expected is None:
            return actual is None
        return normalized_actual is not None

    def oracle_source(self) -> str:
        return (
            "def solve(input_data):\n"
            "    nums = input_data['nums']\n"
            "    target = input_data['target']\n"
            "    for first_index, first_value in enumerate(nums):\n"
            "        for second_index in range(first_index + 1, len(nums)):\n"
            "            if first_value + nums[second_index] == target:\n"
            "                return [first_index, second_index]\n"
            "    return None\n"
        )

    def verify_oracle(self) -> bool:
        return all(
            self.oracle(input_data) == expected
            for input_data, expected in self.official_examples
        )

    @staticmethod
    def encode_input(nums: list[int], target: int) -> dict[str, object]:
        return {"nums": nums, "target": target}
