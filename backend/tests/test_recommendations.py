from types import SimpleNamespace

from fastapi.responses import JSONResponse

from app.api.routes_problems import get_recommendations
from app.main import app
from app.models.catalog import RecommendationCategory, RecommendationsResponse
from app.services.problem_catalog import ProblemCatalog, default_catalog_path
from app.services.recommendations import RecommendationService


def recommendation_service() -> RecommendationService:
    return RecommendationService(ProblemCatalog.from_file(default_catalog_path()))


def test_recommendations_include_one_prerequisite_and_one_related_problem() -> None:
    result = recommendation_service().recommend(current_slug="house-robber")

    assert result is not None
    assert [item.category for item in result.recommendations] == [
        RecommendationCategory.PREREQUISITE,
        RecommendationCategory.RELATED,
    ]
    assert [item.slug for item in result.recommendations] == [
        "best-time-to-buy-and-sell-stock",
        "two-sum",
    ]


def test_recommendations_exclude_solved_and_dismissed_problems() -> None:
    result = recommendation_service().recommend(
        current_slug="house-robber",
        solved_slugs=["best-time-to-buy-and-sell-stock"],
        dismissed_slugs=["two-sum"],
    )

    assert result is not None
    assert all(
        item.slug not in {"best-time-to-buy-and-sell-stock", "two-sum"}
        for item in result.recommendations
    )


def test_recommendations_prioritize_a_weak_shared_pattern() -> None:
    result = recommendation_service().recommend(
        current_slug="two-sum",
        weak_patterns=["hash-map"],
    )

    assert result is not None
    assert result.recommendations[0].slug == "contains-duplicate"
    assert "curated problem catalog and supplied local learning history" in result.basis


def test_recommendations_are_deterministic() -> None:
    service = recommendation_service()

    first = service.recommend(current_slug="number-of-islands")
    second = service.recommend(current_slug="number-of-islands")

    assert first == second


def test_recommendations_endpoint_returns_typed_cards() -> None:
    request = SimpleNamespace(app=app, state=SimpleNamespace(request_id="request-123"))

    result = get_recommendations("house-robber", request)

    assert isinstance(result, RecommendationsResponse)
    assert len(result.recommendations) == 2
    assert result.recommendations[0].explanation


def test_recommendations_endpoint_returns_stable_not_found_error() -> None:
    request = SimpleNamespace(app=app, state=SimpleNamespace(request_id="request-123"))

    result = get_recommendations("not-in-catalog", request)

    assert isinstance(result, JSONResponse)
    assert result.status_code == 404
    assert b'"code":"problem_not_found"' in result.body
