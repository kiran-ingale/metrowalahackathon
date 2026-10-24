"""Constraint-preserving delta debugging for small JSON inputs."""

from __future__ import annotations

import copy
import time
from collections.abc import Callable, Iterator
from typing import Any


def _chunk_removals(value: list[Any] | str) -> Iterator[list[Any] | str]:
    """Yield removals by halves, quarters, then individual items."""
    length = len(value)
    if not length:
        return
    chunk_sizes = dict.fromkeys((max(1, (length + 1) // 2), max(1, (length + 3) // 4), 1))
    for chunk_size in chunk_sizes:
        for start in range(0, length, chunk_size):
            end = min(length, start + chunk_size)
            yield value[:start] + value[end:]


def _integer_candidates(value: int) -> Iterator[int]:
    """Yield strictly smaller integer representatives, without duplicates."""
    half = (abs(value) // 2) * (-1 if value < 0 else 1)
    yielded: set[int] = set()
    for candidate in (0, half, -1, 1):
        if candidate != value and abs(candidate) < abs(value) and candidate not in yielded:
            yielded.add(candidate)
            yield candidate


def _replace_path(root: Any, path: tuple[Any, ...], value: Any) -> Any:
    result = copy.deepcopy(root)
    cursor = result
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    return result


def _walk_paths(value: Any, path: tuple[Any, ...] = ()) -> Iterator[tuple[Any, ...]]:
    """Visit containers before their children, so outer lists shrink first."""
    yield path
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_paths(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_paths(child, path + (index,))


def _get_path(root: Any, path: tuple[Any, ...]) -> Any:
    value = root
    for key in path:
        value = value[key]
    return value


def shrink(
    args: dict,
    fails: Callable[[dict], bool],
    valid: Callable[[dict], bool],
    max_steps: int = 200,
    max_seconds: float = 8.0,
) -> dict:
    """Return the smallest failing, valid JSON-shaped input found within limits.

    Each candidate is constraint-checked before it is run through ``fails``.
    The walk restarts after every successful change and finishes when a complete
    pass cannot simplify the input further.
    """
    deadline = time.monotonic() + max(0.0, max_seconds)
    steps = 0
    best = copy.deepcopy(args)
    stopped = False

    def accept(candidate: dict) -> bool:
        nonlocal steps, stopped
        if steps >= max_steps or time.monotonic() >= deadline:
            stopped = True
            return False
        steps += 1
        probe = copy.deepcopy(candidate)
        if not valid(probe):
            return False
        if time.monotonic() >= deadline:
            stopped = True
            return False
        return bool(fails(copy.deepcopy(candidate)))

    while not stopped:
        progressed = False
        for path in _walk_paths(best):
            value = _get_path(best, path) if path else best
            if path == ():
                # The top-level argument object is not itself a shrink target.
                continue
            if isinstance(value, list) or isinstance(value, str):
                for smaller in _chunk_removals(value):
                    candidate = _replace_path(best, path, smaller)
                    if accept(candidate):
                        best = candidate
                        progressed = True
                        break
                    if stopped:
                        break
            elif isinstance(value, int) and not isinstance(value, bool):
                for smaller in _integer_candidates(value):
                    candidate = _replace_path(best, path, smaller)
                    if accept(candidate):
                        best = candidate
                        progressed = True
                        break
                    if stopped:
                        break
            if progressed or stopped:
                break
        if not progressed:
            break
    return best
