"""Tier 1, sandboxed counterexample search for bundled LeetCode adapters."""

from __future__ import annotations

import ast
import copy
import importlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from verifier.adapters.spec import Spec
from verifier.app.compare import compare
from verifier.app.models import CounterexampleResponse
from verifier.app.sandbox import run_in_sandbox
from verifier.app.shrink import shrink

SUPPORTED_SLUGS = (
    "coin_change",
    "house_robber",
    "maximum_subarray",
    "jump_game",
    "longest_increasing_subsequence",
)
SEED = 1234
GENERATED_INPUTS = 200

_CASE_TIMEOUT = 1.0
_CASE_WALL_TIMEOUT = 4.0
_SHRINK_CASE_TIMEOUT = 0.5
_SHRINK_WALL_TIMEOUT = 1.5


class _VerificationError(Exception):
    pass


def _response(
    status: str,
    *,
    trust_label: str = "could_not_verify",
    input_value: dict[str, Any] | None = None,
    expected: Any = None,
    got: Any = None,
    tests_run: int = 0,
    seed: int = SEED,
    minimized: bool = False,
    reproduced: bool = False,
    limitations: list[str] | None = None,
    message: str,
) -> CounterexampleResponse:
    return CounterexampleResponse(
        status=status,
        trust_label=trust_label,
        input=input_value,
        expected=expected,
        got=got,
        tests_run=tests_run,
        seed=seed,
        minimized=minimized,
        reproduced=reproduced,
        limitations=list(limitations or []),
        message=message,
    )


def _normalize_slug(slug: str) -> str:
    return slug.strip().replace("-", "_")


def _load_spec(slug: str) -> Spec:
    if not isinstance(slug, str):
        raise LookupError("Unsupported problem slug.")
    normalized = _normalize_slug(slug)
    if normalized not in SUPPORTED_SLUGS:
        raise LookupError("Unsupported problem slug.")
    module_name = f"verifier.adapters.{normalized}"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            raise LookupError("Adapter is not installed.") from error
        raise
    spec = getattr(module, "SPEC", None)
    if not isinstance(spec, Spec) or spec.slug != normalized:
        raise _VerificationError(f"Adapter {normalized!r} has no valid Spec.")
    return spec


def _parameter_names(source: str, method: str) -> list[str] | None:
    """Extract ordinary method parameters without executing candidate source."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, TypeError, ValueError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "Solution":
            continue
        for member in node.body:
            if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if member.name != method:
                continue
            if member.args.vararg is not None or member.args.kwarg is not None:
                return None
            names = [arg.arg for arg in (*member.args.posonlyargs, *member.args.args)]
            if names and names[0] in {"self", "cls"}:
                names = names[1:]
            return names
    return None


def _case_mapping(
    source: str,
    method: str,
    args: tuple[Any, ...] | list[Any],
    canonical_names: list[str],
) -> dict[str, Any]:
    names = _parameter_names(source, method)
    if names is None or len(names) != len(args):
        names = canonical_names
    if len(names) != len(args):
        names = [f"arg{index}" for index in range(len(args))]
    return {name: copy.deepcopy(value) for name, value in zip(names, args)}


def _validation_function(spec: Spec):
    namespace: dict[str, Any] = {}
    exec(compile(spec.validate_code, f"<{spec.slug}:validate>", "exec"), namespace)
    validate = namespace.get("validate")
    if not callable(validate):
        raise _VerificationError("Adapter validation code does not define validate(args).")
    return validate


def _ok(outcomes: list[dict[str, Any]], expected_count: int) -> bool:
    return len(outcomes) == expected_count and all(
        isinstance(result, dict) and "ok" in result for result in outcomes
    )




def _cache_key(args: tuple[Any, ...] | list[Any]) -> str:
    return json.dumps(args, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _candidate_status(kind: str) -> str | None:
    if kind == "wrong_output":
        return "found"
    if kind in {"timeout", "skipped"}:
        return "timeout"
    if kind in {"err", "output_too_large", "missing_result", "extra_result"}:
        return "crash"
    return None


def _message_for(kind: str, expected: Any, got: Any) -> str:
    if kind == "wrong_output":
        return f"Candidate returned {got!r}; oracle returned {expected!r}."
    if kind in {"timeout", "skipped"}:
        return "Candidate timed out on a constraint-valid input."
    if kind == "output_too_large":
        return "Candidate produced too much output on a constraint-valid input."
    if kind == "err":
        return f"Candidate raised an error: {got}"
    return "Candidate produced a result that could not be compared safely."


def _tests_completed(results: list[dict[str, Any]]) -> int:
    for index, outcome in enumerate(results):
        if "skipped" in outcome:
            return index
    return len(results)


def run_counterexample(slug: str, code: str) -> CounterexampleResponse:
    """Search seeded, constraint-valid inputs and independently reproduce a hit."""
    try:
        spec = _load_spec(slug)
    except LookupError:
        return _response(
            "not_supported",
            limitations=["Only the bundled Tier 1 adapters are supported."],
            message="This problem slug is not supported.",
        )
    except Exception as error:
        return _response(
            "could_not_verify",
            limitations=[f"Adapter loading failed: {type(error).__name__}."],
            message="The adapter could not be verified.",
        )

    if not isinstance(code, str):
        return _response(
            "could_not_verify",
            limitations=["Candidate source must be a string."],
            message="The candidate could not be verified.",
        )

    limitations = [
        f"Search used {GENERATED_INPUTS} deterministic, small generated inputs; no-mismatch results are not a proof of correctness."
    ]
    try:
        validate = _validation_function(spec)
        oracle_names = _parameter_names(spec.oracle_code, spec.method)
        if oracle_names is None:
            raise _VerificationError("Oracle method parameters could not be read.")

        # First verify the adapter oracle against every published example.
        examples = list(spec.examples)
        if not examples:
            raise _VerificationError("Adapter has no examples to verify its oracle.")
        example_inputs = [
            _case_mapping(spec.oracle_code, spec.method, example.args, oracle_names)
            for example in examples
        ]
        example_results = run_in_sandbox(
            "solve",
            spec.oracle_code,
            spec.method,
            example_inputs,
            per_case_timeout=_CASE_TIMEOUT,
            wall_timeout=_CASE_WALL_TIMEOUT,
        )
        if not _ok(example_results, len(examples)):
            raise _VerificationError("The oracle errored or timed out on an adapter example.")
        for example, actual in zip(examples, example_results):
            if compare([{"ok": example.expected}], [actual]) is not None:
                raise _VerificationError("The oracle disagrees with an adapter example.")

        # Run the adapter's trusted generator in the isolated generator harness.
        generator_source = spec.gen_code.rstrip() + "\n\ndef gen(rng, size):\n    return {'cases': generate_cases(rng, size)}\n"
        generated_result = run_in_sandbox(
            "gen",
            generator_source,
            "gen",
            [{"n": 1, "size": GENERATED_INPUTS, "seed": SEED}],
            per_case_timeout=_CASE_TIMEOUT,
            wall_timeout=_CASE_WALL_TIMEOUT,
        )
        if len(generated_result) != 1 or "ok" not in generated_result[0]:
            raise _VerificationError("The adapter generator failed in its sandbox.")
        generated_batches = generated_result[0]["ok"]
        if (
            not isinstance(generated_batches, list)
            or len(generated_batches) != 1
            or not isinstance(generated_batches[0], dict)
            or not isinstance(generated_batches[0].get("cases"), list)
        ):
            raise _VerificationError("The adapter generator returned an invalid case list.")

        cases = generated_batches[0]["cases"]
        valid_args: list[tuple[Any, ...]] = []
        for args in cases:
            if not isinstance(args, (list, tuple)):
                continue
            try:
                if validate(args):
                    valid_args.append(tuple(copy.deepcopy(args)))
            except Exception:
                # Malformed generated values are filtered out as invalid cases.
                continue
        if not valid_args:
            raise _VerificationError("The generator produced no constraint-valid inputs.")

        oracle_inputs = [
            _case_mapping(spec.oracle_code, spec.method, args, oracle_names)
            for args in valid_args
        ]
        oracle_results = run_in_sandbox(
            "solve",
            spec.oracle_code,
            spec.method,
            oracle_inputs,
            per_case_timeout=_CASE_TIMEOUT,
            wall_timeout=30.0,
        )
        if not _ok(oracle_results, len(valid_args)):
            raise _VerificationError("The oracle failed on a generated input.")

        candidate_names = _parameter_names(code, spec.method)
        if candidate_names is None or len(candidate_names) != len(oracle_names):
            candidate_names = oracle_names
        candidate_inputs = [
            _case_mapping(code, spec.method, args, candidate_names)
            for args in valid_args
        ]
        candidate_results = run_in_sandbox(
            "solve",
            code,
            spec.method,
            candidate_inputs,
            per_case_timeout=_CASE_TIMEOUT,
            wall_timeout=30.0,
        )
        mismatch = compare(oracle_results, candidate_results)
        if mismatch is None:
            return _response(
                "no_mismatch",
                trust_label="examples_checked",
                tests_run=len(valid_args),
                limitations=limitations,
                message=f"No counterexample found in {len(valid_args)} tests.",
            )

        initial_index = mismatch.get("index", 0)
        original_args = valid_args[initial_index]
        original_kind = mismatch["kind"]
        if _candidate_status(original_kind) is None:
            return _response(
                "could_not_verify",
                tests_run=min(len(valid_args), initial_index + 1),
                limitations=limitations + ["The mismatch was not a candidate outcome."],
                message="The candidate mismatch could not be verified.",
            )

        # Reuse the batch results during shrinking, then run a fresh pair of
        # sandboxes for every new candidate and again for the final witness.
        outcomes: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
            _cache_key(args): (oracle_result, candidate_result)
            for args, oracle_result, candidate_result in zip(
                valid_args, oracle_results, candidate_results
            )
        }

        def evaluate(args: tuple[Any, ...] | list[Any], *, fresh: bool = False):
            key = _cache_key(args)
            if not fresh and key in outcomes:
                oracle_result, candidate_result = outcomes[key]
                return oracle_result, candidate_result
            oracle_one = run_in_sandbox(
                "solve",
                spec.oracle_code,
                spec.method,
                [_case_mapping(spec.oracle_code, spec.method, args, oracle_names)],
                per_case_timeout=_SHRINK_CASE_TIMEOUT,
                wall_timeout=_SHRINK_WALL_TIMEOUT,
            )
            candidate_one = run_in_sandbox(
                "solve",
                code,
                spec.method,
                [_case_mapping(code, spec.method, args, candidate_names)],
                per_case_timeout=_SHRINK_CASE_TIMEOUT,
                wall_timeout=_SHRINK_WALL_TIMEOUT,
            )
            pair = (
                oracle_one[0] if oracle_one else {"timeout": True},
                candidate_one[0] if candidate_one else {"timeout": True},
            )
            outcomes[key] = pair
            return pair

        def shrink_valid(candidate: dict[str, Any]) -> bool:
            try:
                args = tuple(candidate[name] for name in oracle_names)
                return bool(validate(args))
            except (KeyError, TypeError, ValueError):
                return False

        def shrink_fails(candidate: dict[str, Any]) -> bool:
            try:
                args = tuple(candidate[name] for name in oracle_names)
                oracle_one, candidate_one = evaluate(args)
                found = compare([oracle_one], [candidate_one])
                return found is not None and found["kind"] == original_kind
            except Exception:
                return False

        original_input = {
            name: copy.deepcopy(value)
            for name, value in zip(oracle_names, original_args)
        }
        minimized_input = shrink(
            original_input,
            shrink_fails,
            shrink_valid,
            max_steps=200,
            max_seconds=8.0,
        )
        final_args = tuple(minimized_input[name] for name in oracle_names)

        # Do not report a witness unless both programs independently reproduce
        # the same kind of failure on the final, still-valid input.
        if not shrink_valid(minimized_input):
            raise _VerificationError("The minimized input failed adapter validation.")
        final_oracle, final_candidate = evaluate(final_args, fresh=True)
        final_mismatch = compare([final_oracle], [final_candidate])
        if (
            final_mismatch is None
            or final_mismatch["kind"] != original_kind
            or final_mismatch["kind"].startswith("oracle_")
        ):
            return _response(
                "could_not_verify",
                tests_run=min(len(valid_args), initial_index + 1),
                limitations=limitations + ["The final shrunken input did not reproduce."],
                message="A counterexample candidate was found, but it did not reproduce after shrinking.",
            )

        status = _candidate_status(final_mismatch["kind"])
        if status is None:
            raise _VerificationError("The final result has an unsupported mismatch kind.")
        final_input = {
            name: copy.deepcopy(value)
            for name, value in zip(oracle_names, final_args)
        }
        return _response(
            status,
            trust_label="verified_counterexample",
            input_value=final_input,
            expected=final_mismatch.get("expected"),
            got=final_mismatch.get("got"),
            tests_run=_tests_completed(candidate_results),
            minimized=final_input != original_input,
            reproduced=True,
            limitations=limitations,
            message=_message_for(
                final_mismatch["kind"],
                final_mismatch.get("expected"),
                final_mismatch.get("got"),
            ),
        )
    except Exception as error:
        return _response(
            "could_not_verify",
            limitations=limitations + [f"Verification failed: {type(error).__name__}."],
            message="The candidate could not be verified.",
        )

