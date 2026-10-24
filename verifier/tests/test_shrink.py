from copy import deepcopy

from verifier.app.shrink import shrink


def test_shrinks_list_to_minimum():
    fails = lambda a: 3 in a["coins"] and 4 in a["coins"]
    valid = lambda a: len(a["coins"]) >= 1
    out = shrink({"coins": [1, 9, 3, 7, 4, 2], "amount": 6}, fails, valid)
    assert sorted(out["coins"]) == [3, 4]


def test_never_returns_invalid_input():
    fails = lambda a: True
    valid = lambda a: len(a["coins"]) >= 1
    out = shrink({"coins": [5, 6, 7], "amount": 10}, fails, valid)
    assert len(out["coins"]) >= 1


def test_valid_is_checked_before_fails_for_each_candidate():
    events = []

    def valid(candidate):
        events.append(("valid", deepcopy(candidate)))
        return len(candidate["values"]) >= 2

    def fails(candidate):
        events.append(("fails", deepcopy(candidate)))
        assert len(candidate["values"]) >= 2
        return False

    shrink({"values": [1, 2, 3]}, fails, valid, max_steps=20)

    for index, (kind, candidate) in enumerate(events):
        if kind == "fails":
            assert index > 0
            assert events[index - 1] == ("valid", candidate)


def test_nested_lists_try_outer_removals_before_inner_removals():
    seen = []

    def valid(candidate):
        seen.append(deepcopy(candidate))
        return True

    shrink(
        {"grid": [[1, 2], [3, 4]]},
        fails=lambda _candidate: False,
        valid=valid,
        max_steps=20,
    )

    assert seen[0] == {"grid": [[3, 4]]}
    assert seen[1] == {"grid": [[1, 2]]}
    assert seen[2] == {"grid": [[2], [3, 4]]}


def test_string_shrinks_like_a_list():
    out = shrink(
        {"text": "abzcd"},
        fails=lambda candidate: "z" in candidate["text"],
        valid=lambda _candidate: True,
    )
    assert out == {"text": "z"}


def test_integer_shrinking_does_not_oscillate_around_zero():
    out = shrink(
        {"value": 0},
        fails=lambda candidate: candidate["value"] in {-1, 0},
        valid=lambda _candidate: True,
    )
    assert out == {"value": 0}
