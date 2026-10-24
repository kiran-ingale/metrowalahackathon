from fastapi.testclient import TestClient

from verifier.app.main import app


client = TestClient(app)


def test_coin_change_returns_reproduced_counterexample() -> None:
    response = client.post(
        "/counterexample",
        json={
            "slug": "coin-change",
            "statement": "Make amount with fewest coins",
            "code": """class Solution:\n    def coinChange(self, coins, amount):\n        count = 0\n        for coin in sorted(coins, reverse=True):\n            count += amount // coin\n            amount %= coin\n        return count if amount == 0 else -1\n""",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "found"
    assert body["trust_label"] == "verified_counterexample"
    assert body["input"] is not None
    assert body["reproduced"] is True


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
            "code": "pass",
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
