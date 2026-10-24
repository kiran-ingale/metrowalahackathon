from verifier.adapters.coin_change import SPEC as COIN_CHANGE
from verifier.app.compare import compare
from verifier.app.sandbox import run_in_sandbox

GREEDY_COIN_CHANGE = '''
class Solution:
    def coinChange(self, coins, amount):
        coins = sorted(coins, reverse=True)
        used = 0
        for coin in coins:
            used += amount // coin
            amount %= coin
        return used if amount == 0 else -1
'''


def run_coin_change(source: str) -> list[dict[str, object]]:
    return run_in_sandbox(
        "solve",
        source,
        COIN_CHANGE.method,
        [{"coins": [1, 3, 4], "amount": 6}],
        per_case_timeout=2.0,
        wall_timeout=6.0,
    )


def test_internal_runner_executes_both_candidates_before_reporting_mismatch() -> None:
    oracle = run_coin_change(COIN_CHANGE.oracle_code)
    candidate = run_coin_change(GREEDY_COIN_CHANGE)

    mismatch = compare(oracle, candidate)

    assert oracle == [{"ok": 2}]
    assert candidate == [{"ok": 3}]
    assert mismatch == {
        "index": 0,
        "kind": "wrong_output",
        "expected": 2,
        "got": 3,
    }


def test_correct_candidate_does_not_produce_a_counterexample() -> None:
    oracle = run_coin_change(COIN_CHANGE.oracle_code)
    candidate = run_coin_change(COIN_CHANGE.oracle_code)

    assert compare(oracle, candidate) is None
