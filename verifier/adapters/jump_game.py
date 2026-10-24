"""LeetCode 55: Jump Game."""

from verifier.adapters.spec import Example, Spec


SPEC = Spec(
    slug="jump_game",
    method="canJump",
    oracle_code='''
class Solution:
    def canJump(self, nums):
        # Exhaustively traverse every position reachable by a legal jump.
        target = len(nums) - 1
        pending = [0]
        seen = {0}
        while pending:
            index = pending.pop()
            if index == target:
                return True
            for next_index in range(index + 1, min(target, index + nums[index]) + 1):
                if next_index not in seen:
                    seen.add(next_index)
                    pending.append(next_index)
        return False
''',
    gen_code='''
def generate_cases(rng, count):
    cases = [([0, 0, 5, 0],), ([2, 3, 1, 1, 4],), ([3, 2, 1, 0, 4],)]
    while len(cases) < count:
        size = rng.randint(1, 8)
        nums = [rng.randint(0, size + 1) for _ in range(size)]
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
        and 1 <= len(nums) <= 10_000
        and all(type(value) is int and 0 <= value <= 100_000 for value in nums)
    )
''',
    examples=(
        Example(args=([2, 3, 1, 1, 4],), expected=True),
        Example(args=([3, 2, 1, 0, 4],), expected=False),
    ),
    invalid_input=([-1],),
)
