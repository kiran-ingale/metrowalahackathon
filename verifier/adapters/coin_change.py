"""LeetCode 322: Coin Change."""

from verifier.adapters.spec import Example, Spec


SPEC = Spec(
    slug="coin_change",
    method="coinChange",
    oracle_code='''
from collections import deque

class Solution:
    def coinChange(self, coins, amount):
        # Exhaustively search the graph of reachable totals by number of coins.
        if amount == 0:
            return 0
        queue = deque([(0, 0)])
        seen = {0}
        while queue:
            total, used = queue.popleft()
            for coin in coins:
                next_total = total + coin
                if next_total == amount:
                    return used + 1
                if next_total < amount and next_total not in seen:
                    seen.add(next_total)
                    queue.append((next_total, used + 1))
        return -1
''',
    gen_code='''
def generate_cases(rng, count):
    cases = [([1, 3, 4], 6), ([2, 5], 3), ([1], 0)]
    while len(cases) < count:
        coins = sorted(set(rng.randint(1, 7) for _ in range(rng.randint(1, 4))))
        amount = rng.randint(0, 18)
        cases.append((coins, amount))
    return cases[:count]
''',
    validate_code='''
def validate(args):
    if not isinstance(args, (tuple, list)) or len(args) != 2:
        return False
    coins, amount = args
    return (
        isinstance(coins, (tuple, list))
        and 1 <= len(coins) <= 12
        and all(type(coin) is int and 1 <= coin <= 2**31 - 1 for coin in coins)
        and len(set(coins)) == len(coins)
        and type(amount) is int
        and 0 <= amount <= 10_000
    )
''',
    examples=(
        Example(args=([1, 2, 5], 11), expected=3),
        Example(args=([2], 3), expected=-1),
        Example(args=([1], 0), expected=0),
    ),
    invalid_input=([1], 10_001),
)
