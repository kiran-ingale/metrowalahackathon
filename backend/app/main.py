from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_counterexamples import router as counterexamples_router
from app.api.routes_guidance import router as guidance_router
from app.api.routes_problems import router as problems_router
from app.core.body_limit import RequestBodyLimitMiddleware
from app.core.errors import unhandled_exception_handler, validation_exception_handler
from app.core.request_id import RequestIdMiddleware
from app.core.settings import Settings, get_settings
from app.models.responses import HealthResponse
from app.services.counterexamples.service import CounterexampleService
from app.services.guidance import GuidanceService
from app.services.llm_client import OpenAIResponsesClient, UnconfiguredLLMClient
from app.services.problem_catalog import ProblemCatalog, load_default_catalog


def create_guidance_service(settings: Settings, catalog: ProblemCatalog) -> GuidanceService:
    if settings.openai_api_key and settings.openai_model:
        client = OpenAIResponsesClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )
    else:
        client = UnconfiguredLLMClient()
    return GuidanceService(client=client, catalog=catalog)


def create_app(
    settings: Settings | None = None,
    guidance_service: GuidanceService | None = None,
    counterexample_service: CounterexampleService | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    application = FastAPI(title=app_settings.app_name, version=app_settings.app_version)
    catalog = load_default_catalog()
    application.state.problem_catalog = catalog
    application.state.guidance_service = guidance_service or create_guidance_service(
        app_settings, catalog
    )
    application.state.counterexample_service = (
        counterexample_service or CounterexampleService(catalog)
    )
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_size=app_settings.request_body_limit_bytes,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
    application.include_router(guidance_router)
    application.include_router(problems_router)
    application.include_router(counterexamples_router)

    @application.get("/health", response_model=HealthResponse)
    def health_check() -> HealthResponse:
        return HealthResponse(
            service="unstuck-api",
            version=application.version,
            status="ok",
        )

    return application

app = create_app()
