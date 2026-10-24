from app.main import app


def test_health_check_returns_service_status() -> None:
    health_route = next(route for route in app.routes if getattr(route, "path", None) == "/health")
    response = health_route.endpoint()

    assert response.model_dump() == {
        "service": "unstuck-api",
        "version": "0.1.0",
        "status": "ok",
    }
    assert "/health" in app.openapi()["paths"]
