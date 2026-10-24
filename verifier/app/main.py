from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .middleware import RequestBodyLimitMiddleware
from .models import CounterexampleRequest, CounterexampleResponse
from .orchestrator import run_counterexample


app = FastAPI(title="Unstuck Verifier API")
app.add_middleware(RequestBodyLimitMiddleware, max_body_size=1024 * 1024)
app.add_middleware(
    # Chrome extension IDs contain 32 lowercase characters in the range a-p.
    CORSMiddleware,
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


@app.post("/counterexample", response_model=CounterexampleResponse)
def counterexample(request: CounterexampleRequest) -> CounterexampleResponse:
    return run_counterexample(request.slug, request.code)
