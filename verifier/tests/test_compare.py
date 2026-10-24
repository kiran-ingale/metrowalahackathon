from verifier.app.compare import compare


def test_float_results_use_isclose():
    assert compare([{"ok": 1.0}], [{"ok": 1.0 + 1e-10}]) is None


def test_normalize_is_applied_before_value_comparison():
    assert compare(
        [{"ok": [1, 2, 3]}],
        [{"ok": [3, 2, 1]}],
        normalize=sorted,
    ) is None


def test_wrong_output_error_and_timeout_are_distinct():
    oracle = [{"ok": 4}]

    assert compare(oracle, [{"ok": 5}])["kind"] == "wrong_output"
    assert compare(oracle, [{"err": "ValueError: bad"}])["kind"] == "err"
    assert compare(oracle, [{"timeout": True}])["kind"] == "timeout"
