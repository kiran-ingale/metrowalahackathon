from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.responses import JSONResponse

from app.api.routes_problems import get_problem
from app.main import app
from app.models.catalog import ProblemMetadataResponse
from app.services.problem_catalog import (
    CatalogValidationError,
    ProblemCatalog,
    default_catalog_path,
)

FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "catalog"


@pytest.mark.parametrize(
    "fixture_name",
    ["duplicate_slugs.json", "missing_reference.json", "circular_prerequisites.json"],
)
def test_catalog_rejects_invalid_fixture_data(fixture_name: str) -> None:
    with pytest.raises(CatalogValidationError):
        ProblemCatalog.from_file(FIXTURES_DIRECTORY / fixture_name)


def test_default_catalog_loads_two_sum_metadata() -> None:
    catalog = ProblemCatalog.from_file(default_catalog_path())

    assert len(catalog) >= 10
    assert catalog.get("two-sum").title == "Two Sum"


def test_problem_endpoint_returns_public_metadata() -> None:
    request = SimpleNamespace(app=app, state=SimpleNamespace(request_id="request-123"))

    response = get_problem("two-sum", request)

    assert isinstance(response, ProblemMetadataResponse)
    assert response.slug == "two-sum"
    assert "counterexample_support" not in response.model_dump()


def test_problem_endpoint_returns_stable_not_found_error() -> None:
    request = SimpleNamespace(app=app, state=SimpleNamespace(request_id="request-123"))

    response = get_problem("not-in-catalog", request)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert response.body == (
        b'{"code":"problem_not_found","message":"The requested problem is not available '
        b'in the catalog.","request_id":"request-123","retryable":false}'
    )
