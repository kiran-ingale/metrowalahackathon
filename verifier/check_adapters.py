"""Check the bundled oracles, generators, validators, and golden programs.

Run from the project root with ``python -m verifier.check_adapters``.
"""

from __future__ import annotations

import copy
import importlib
import json
import random
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from verifier.adapters.spec import Spec  # noqa: E402


ADAPTERS = (
    "coin_change",
    "house_robber",
    "maximum_subarray",
    "jump_game",
    "longest_increasing_subsequence",
)
SEED = 20_261_024
GENERATED_CASE_COUNT = 128


def _load_callable(source: str, name: str) -> Any:
    namespace: dict[str, Any] = {}
    exec(compile(source, f"<{name}>", "exec"), namespace)
    return namespace[name]


def _run_program(source: str, method: str, args: tuple[Any, ...]) -> Any:
    namespace: dict[str, Any] = {}
    exec(compile(source, f"<{method}>", "exec"), namespace)
    solution = namespace["Solution"]()
    return getattr(solution, method)(*copy.deepcopy(args))


def _capture(source: str, method: str, args: tuple[Any, ...]) -> tuple[bool, Any]:
    try:
        return True, _run_program(source, method, args)
    except Exception as error:  # A crash is a failing behavior for the golden code.
        return False, f"{type(error).__name__}: {error}"


def _load_spec(slug: str) -> Spec:
    module = importlib.import_module(f"verifier.adapters.{slug}")
    spec = module.SPEC
    if not isinstance(spec, Spec):
        raise TypeError(f"{slug}: SPEC is not a Spec")
    return spec


def check_spec(slug: str) -> list[str]:
    errors: list[str] = []
    spec = _load_spec(slug)
    golden_path = ROOT / "verifier" / "golden" / f"{slug}.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    if golden.get("slug") != slug:
        errors.append("golden slug does not match adapter")

    validator = _load_callable(spec.validate_code, "validate")
    generator = _load_callable(spec.gen_code, "generate_cases")

    # The oracle must agree with every published example.
    for number, example in enumerate(spec.examples, start=1):
        try:
            actual = _run_program(spec.oracle_code, spec.method, example.args)
            if actual != example.expected:
                errors.append(
                    f"oracle example {number}: expected {example.expected!r}, got {actual!r}"
                )
        except Exception as error:
            errors.append(f"oracle example {number} raised {type(error).__name__}: {error}")

    # Golden wrong programs must pass the examples, while correct programs must
    # agree with the oracle on both examples and seeded generated cases.
    for number, example in enumerate(spec.examples, start=1):
        success, actual = _capture(golden["wrong_code"], spec.method, example.args)
        if not success or actual != example.expected:
            errors.append(f"wrong_code does not pass example {number}: {actual!r}")
        success, actual = _capture(golden["correct_code"], spec.method, example.args)
        if not success or actual != example.expected:
            errors.append(f"correct_code fails example {number}: {actual!r}")

    generated = generator(random.Random(SEED), GENERATED_CASE_COUNT)
    found_mismatch = False
    for number, args in enumerate(generated, start=1):
        if not validator(args):
            errors.append(f"generator case {number} violates the adapter constraints")
            continue
        try:
            expected = _run_program(spec.oracle_code, spec.method, args)
        except Exception as error:
            errors.append(f"oracle generated case {number} raised {type(error).__name__}: {error}")
            continue

        correct_ok, correct_actual = _capture(golden["correct_code"], spec.method, args)
        if not correct_ok or correct_actual != expected:
            errors.append(f"correct_code disagrees with oracle on generated case {number}")

        wrong_ok, wrong_actual = _capture(golden["wrong_code"], spec.method, args)
        if not wrong_ok or wrong_actual != expected:
            found_mismatch = True

    if not generated:
        errors.append("generator returned no small inputs")
    if not found_mismatch:
        errors.append("oracle and wrong_code never differ on a generated small input")

    if validator(spec.invalid_input):
        errors.append(f"validator accepted out-of-constraint input {spec.invalid_input!r}")

    # The named counterexample is an additional, readable witness in the fixture.
    witness = tuple(golden.get("counterexample_args", ()))
    if witness:
        try:
            oracle_value = _run_program(spec.oracle_code, spec.method, witness)
            wrong_ok, wrong_value = _capture(golden["wrong_code"], spec.method, witness)
            if wrong_ok and oracle_value == wrong_value:
                errors.append("golden counterexample does not distinguish wrong_code from oracle")
        except Exception as error:
            errors.append(f"golden counterexample check raised {type(error).__name__}: {error}")

    return errors


def main() -> int:
    failed = False
    for slug in ADAPTERS:
        errors = check_spec(slug)
        if errors:
            failed = True
            for error in errors:
                print(f"FAIL {slug}: {error}")
        else:
            print(f"PASS {slug}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
