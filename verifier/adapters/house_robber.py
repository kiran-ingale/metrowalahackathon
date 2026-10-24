"""LeetCode 198: House Robber."""

from verifier.adapters.spec import Example, Spec


SPEC = Spec(
    slug="house_robber",
    method="rob",
    oracle_code='''
class Solution:
    def rob(self, nums):
        # Enumerate every subset and keep only subsets without adjacent houses.
        best = 0
        for mask in range(1 << len(nums)):
            if mask & (mask << 1):
                continue
            total = sum(value for index, value in enumerate(nums) if mask & (1 << index))
            best = max(best, total)
        return best
''',
    gen_code='''
def generate_cases(rng, count):
    cases = [([1],), ([2, 1, 1, 2],), ([0, 0, 0],)]
    while len(cases) < count:
        nums = [rng.randint(0, 15) for _ in range(rng.randint(1, 8))]
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
        and 1 <= len(nums) <= 100
        and all(type(value) is int and 0 <= value <= 400 for value in nums)
    )
''',
    examples=(
        Example(args=([1, 2, 3, 1],), expected=4),
        Example(args=([2, 7, 9, 3, 1],), expected=12),
    ),
    invalid_input=([401],),
)
