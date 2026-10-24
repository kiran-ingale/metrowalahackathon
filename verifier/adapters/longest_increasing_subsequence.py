"""LeetCode 300: Longest Increasing Subsequence."""

from verifier.adapters.spec import Example, Spec


SPEC = Spec(
    slug="longest_increasing_subsequence",
    method="lengthOfLIS",
    oracle_code='''
class Solution:
    def lengthOfLIS(self, nums):
        # Enumerate subsequences and keep the longest strictly increasing one.
        best = 0
        for mask in range(1 << len(nums)):
            previous = None
            length = 0
            increasing = True
            for index, value in enumerate(nums):
                if mask & (1 << index):
                    if previous is not None and value <= previous:
                        increasing = False
                        break
                    previous = value
                    length += 1
            if increasing:
                best = max(best, length)
        return best
''',
    gen_code='''
def generate_cases(rng, count):
    cases = [([2, 2, 3],), ([10, 9, 2, 5, 3, 7, 101, 18],), ([1, 3, 5, 4, 7],)]
    while len(cases) < count:
        nums = [rng.randint(-5, 5) for _ in range(rng.randint(1, 9))]
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
        and 1 <= len(nums) <= 2_500
        and all(type(value) is int and -10_000 <= value <= 10_000 for value in nums)
    )
''',
    examples=(
        Example(args=([10, 9, 2, 5, 3, 7, 101, 18],), expected=4),
        Example(args=([1, 3, 5, 4, 7],), expected=4),
    ),
    invalid_input=([10_001],),
)
