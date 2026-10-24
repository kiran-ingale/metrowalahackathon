from fastapi.testclient import TestClient

from verifier.app.main import app


client = TestClient(app)


def test_coin_change_returns_mock_counterexample() -> None:
    response = client.post(
        "/counterexample",
        json={"slug": "coin-change", "statement": "Make amount with fewest coins", "code": ""},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "found",
        "trust_label": "verified_counterexample",
        "input": {"coins": [1, 3, 4], "amount": 6},
        "expected": 2,
        "got": 3,
        "tests_run": 200,
        "seed": 1234,
        "minimized": True,
        "reproduced": True,
        "limitations": [],
        "message": "Greedy picks 4+1+1 (3 coins); optimal is 3+3 (2 coins)",
    }


def test_other_slug_is_not_supported() -> None:
    response = client.post(
        "/counterexample",
        json={"slug": "unknown", "statement": "Any statement", "code": "pass"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "not_supported"
    assert response.json()["trust_label"] == "could_not_verify"


def test_unknown_request_field_is_rejected() -> None:
    response = client.post(
        "/counterexample",
        json={
            "slug": "coin-change",
            "statement": "Make amount with fewest coins",
            "code": "",
            "debug": True,
        },
    )

    assert response.status_code == 422


def test_cors_allows_chrome_extension_origins_only() -> None:
    allowed_origin = f"chrome-extension://{'a' * 32}"
    payload = {"slug": "unknown", "statement": "Any statement", "code": "pass"}

    allowed_response = client.post(
        "/counterexample", json=payload, headers={"Origin": allowed_origin}
    )
    disallowed_response = client.post(
        "/counterexample", json=payload, headers={"Origin": "https://example.com"}
    )

    assert allowed_response.headers["access-control-allow-origin"] == allowed_origin
    assert "access-control-allow-origin" not in disallowed_response.headers


def test_request_body_over_one_megabyte_is_rejected() -> None:
    response = client.post("/counterexample", content=b"x" * (1024 * 1024 + 1))

    assert response.status_code == 413
