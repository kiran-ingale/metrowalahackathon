from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from verifier.app import sandbox
from verifier.app.sandbox import run_in_sandbox


def run(code: str, inputs: list[dict], *, timeout: float = 2.0) -> list[dict]:
    return run_in_sandbox(
        "solve",
        code,
        "solve",
        inputs,
        per_case_timeout=timeout,
        wall_timeout=max(timeout * max(len(inputs), 1) + 2.0, 3.0),
    )


def test_infinite_loop_times_out_current_case_and_skips_later_cases() -> None:
    code = """
class Solution:
    def solve(self, value):
        if value == 2:
            while True:
                pass
        return value * 10
"""
    results = run(code, [{"value": 1}, {"value": 2}, {"value": 3}], timeout=0.4)

    assert results == [{"ok": 10}, {"timeout": True}, {"skipped": True}]


def test_print_spam_is_suppressed_and_does_not_corrupt_protocol() -> None:
    code = """
class Solution:
    def solve(self, value):
        for _ in range(5000):
            print('spam' * 100)
        return value + 1
"""
    assert run(code, [{"value": 4}, {"value": 9}]) == [{"ok": 5}, {"ok": 10}]


def test_result_larger_than_stdout_limit_is_reported() -> None:
    code = """
class Solution:
    def solve(self, value):
        return 'x' * (1024 * 1024 + 10)
"""
    results = run(code, [{"value": 1}, {"value": 2}], timeout=5.0)

    assert results == [{"output_too_large": True}, {"skipped": True}]


def test_memory_bomb_is_contained() -> None:
    code = """
class Solution:
    def solve(self, value):
        return len(bytearray(300 * 1024 * 1024))
"""
    results = run(code, [{"value": 1}], timeout=5.0)

    assert len(results) == 1
    assert "err" in results[0]
    assert results[0]["err"].startswith("MemoryError:")


def test_os_system_output_is_not_exposed() -> None:
    code = """
import os
class Solution:
    def solve(self, value):
        os.system('echo hi')
        return value
"""
    assert run(code, [{"value": 7}]) == [{"ok": 7}]


def test_deep_recursion_is_a_normal_case_error() -> None:
    code = """
class Solution:
    def descend(self, depth):
        if depth == 0:
            return 0
        return self.descend(depth - 1) + 1
    def solve(self, depth):
        return self.descend(depth)
"""
    results = run(code, [{"depth": 5000}])

    assert len(results) == 1
    assert results[0]["err"].startswith("RecursionError:")


def test_candidate_can_swallow_its_own_exception() -> None:
    code = """
class Solution:
    def solve(self, value):
        try:
            return 1 // 0
        except ZeroDivisionError:
            return value
"""
    assert run(code, [{"value": 23}]) == [{"ok": 23}]


def test_mutated_inputs_do_not_leak_between_cases_or_to_parent() -> None:
    code = """
class Solution:
    def solve(self, values):
        values.append('changed')
        return values
"""
    inputs = [{"values": ["original"]}, {"values": ["original"]}]

    results = run(code, inputs)

    assert results == [
        {"ok": ["original", "changed"]},
        {"ok": ["original", "changed"]},
    ]
    assert inputs == [{"values": ["original"]}, {"values": ["original"]}]


def test_sandbox_cwd_and_files_are_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox.tempfile, "tempdir", str(tmp_path))
    code = """
class Solution:
    def solve(self, value):
        with open('candidate-output.txt', 'w', encoding='utf-8') as output:
            output.write('private')
        return value
"""

    assert run(code, [{"value": 11}]) == [{"ok": 11}]
    assert list(tmp_path.iterdir()) == []


def test_generator_mode_returns_seeded_argument_dictionaries() -> None:
    code = """
def gen(rng, size):
    return {'values': [rng.randrange(10) for _ in range(size)]}
"""
    result = run_in_sandbox(
        "gen",
        code,
        "gen",
        [{"n": 3, "size": 4, "seed": 91}],
        per_case_timeout=2.0,
        wall_timeout=5.0,
    )

    assert len(result) == 1
    assert len(result[0]["ok"]) == 3
    assert all(isinstance(item, dict) and len(item["values"]) == 4 for item in result[0]["ok"])
    assert result == run_in_sandbox(
        "gen",
        code,
        "gen",
        [{"n": 3, "size": 4, "seed": 91}],
        per_case_timeout=2.0,
        wall_timeout=5.0,
    )
