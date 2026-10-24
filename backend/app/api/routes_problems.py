from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.errors import api_error_response, request_id_for
from app.models.catalog import ProblemMetadataResponse, RecommendationsResponse
from app.services.problem_catalog import ProblemCatalog
from app.services.recommendations import RecommendationService

router = APIRouter(prefix="/v1/problems", tags=["problems"])


def get_catalog(request: Request) -> ProblemCatalog:
    return request.app.state.problem_catalog


@router.get("/{slug}/recommendations", response_model=RecommendationsResponse)
def get_recommendations(
    slug: str,
    request: Request,
    solved_slug: list[str] | None = None,
    dismissed_slug: list[str] | None = None,
    weak_pattern: list[str] | None = None,
) -> RecommendationsResponse | JSONResponse:
    response = RecommendationService(get_catalog(request)).recommend(
        current_slug=slug,
        solved_slugs=solved_slug or [],
        dismissed_slugs=dismissed_slug or [],
        weak_patterns=weak_pattern or [],
    )
    if response is None:
        return api_error_response(
            status_code=404,
            code="problem_not_found",
            message="The requested problem is not available in the catalog.",
            request_id=request_id_for(request),
            retryable=False,
        )
    return response


@router.get("/{slug}", response_model=ProblemMetadataResponse)
def get_problem(slug: str, request: Request) -> ProblemMetadataResponse | JSONResponse:
    problem = get_catalog(request).get(slug)
    if problem is None:
        return api_error_response(
            status_code=404,
            code="problem_not_found",
            message="The requested problem is not available in the catalog.",
            request_id=request_id_for(request),
            retryable=False,
        )
    return ProblemMetadataResponse.from_catalog_problem(problem)
