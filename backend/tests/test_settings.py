from app.core.request_id import resolve_request_id
from app.core.settings import Settings
from app.main import create_app


def test_settings_parse_comma_separated_allowed_origins() -> None:
    settings = Settings(
        allowed_origins="http://localhost:5173,chrome-extension://example",
        openai_api_key=None,
    )

    assert settings.allowed_origins == [
        "http://localhost:5173",
        "chrome-extension://example",
    ]


def test_invalid_request_id_is_replaced() -> None:
    request_id = resolve_request_id("unsafe request id")

    assert request_id != "unsafe request id"
    assert len(request_id) == 36


def test_application_registers_restricted_cors_configuration() -> None:
    application = create_app(
        Settings(
            allowed_origins=["chrome-extension://example"],
            openai_api_key=None,
        )
    )
    cors_middleware = next(
        middleware
        for middleware in application.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    )

    assert cors_middleware.kwargs["allow_origins"] == ["chrome-extension://example"]
    assert cors_middleware.kwargs["allow_methods"] == ["GET", "POST", "OPTIONS"]
