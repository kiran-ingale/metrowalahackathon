from fastapi.testclient import TestClient

from app.main import create_app

WRONG_TWO_SUM = """\
def solve(input_data):
    return [0, 1]
"""


def request_payload(*, confirm_execution: bool | None = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "context": {
            "slug": "two-sum",
            "title": "Two Sum",
            "statement": "Return the indices of two values that add to a target.",
            "language": "python",
            "code": WRONG_TWO_SUM,
        }
    }
    if confirm_execution is not None:
        payload["confirm_execution"] = confirm_execution
    return payload


def test_canonical_counterexample_route_requires_explicit_execution_consent() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/counterexamples/find",
        json=request_payload(confirm_execution=None),
    )

    assert response.status_code == 422


def test_canonical_route_reports_only_a_reproduced_mismatch() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/v1/counterexamples/find",
        json=request_payload(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "found"
    assert response.json()["input"] is not None
    assert response.json()["expected"] != response.json()["actual"]


def test_retired_verifier_route_is_not_public_on_backend() -> None:
    client = TestClient(create_app())

    response = client.post("/counterexample", json=request_payload())

    assert response.status_code == 404
