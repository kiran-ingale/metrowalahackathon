"""LeetCode 53: Maximum Subarray."""

from verifier.adapters.spec import Example, Spec


SPEC = Spec(
    slug="maximum_subarray",
    method="maxSubArray",
    oracle_code='''
class Solution:
    def maxSubArray(self, nums):
        # Try every contiguous interval and take its largest sum.
        best = nums[0]
        for start in range(len(nums)):
            total = 0
            for end in range(start, len(nums)):
                total += nums[end]
                best = max(best, total)
        return best
''',
    gen_code='''
def generate_cases(rng, count):
    cases = [([-3, -1, -2],), ([5],), ([1, -1, 1],)]
    while len(cases) < count:
        nums = [rng.randint(-9, 9) for _ in range(rng.randint(1, 8))]
        cases.append((nums,))
    return cases[:count]
''',
    validate_code='''
def validate(args):
    if not isinstance(args, (tuple, list)) or len(args) != 1:
        return False
    (nums,) = args
    return (
        isinstance(nums, (tuple, list))
        and 1 <= len(nums) <= 100_000
        and all(type(value) is int and -10_000 <= value <= 10_000 for value in nums)
    )
''',
    examples=(
        Example(args=([-2, 1, -3, 4, -1, 2, 1, -5, 4],), expected=6),
        Example(args=([1],), expected=1),
    ),
    invalid_input=([10_001],),
)
