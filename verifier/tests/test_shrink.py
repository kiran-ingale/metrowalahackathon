from verifier.app.shrink import shrink


def test_shrinks_list_to_minimum():
    fails = lambda a: 3 in a["coins"] and 4 in a["coins"]
    valid = lambda a: len(a["coins"]) >= 1
    out = shrink({"coins": [1, 9, 3, 7, 4, 2], "amount": 6}, fails, valid)
    assert sorted(out["coins"]) == [3, 4]


def test_never_returns_invalid_input():
    fails = lambda a: True              # everything "fails"
    valid = lambda a: len(a["coins"]) >= 1
    out = shrink({"coins": [5, 6, 7], "amount": 10}, fails, valid)
    assert len(out["coins"]) >= 1       # must not shrink to an empty list