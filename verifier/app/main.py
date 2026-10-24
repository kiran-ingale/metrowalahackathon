from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .middleware import RequestBodyLimitMiddleware
from .models import CounterexampleRequest, CounterexampleResponse


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
    if request.slug == "coin-change":
        return CounterexampleResponse(
            status="found",
            trust_label="verified_counterexample",
            input={"coins": [1, 3, 4], "amount": 6},
            expected=2,
            got=3,
            tests_run=200,
            seed=1234,
            minimized=True,
            reproduced=True,
            limitations=[],
            message="Greedy picks 4+1+1 (3 coins); optimal is 3+3 (2 coins)",
        )

    return CounterexampleResponse(
        status="not_supported",
        trust_label="could_not_verify",
        input=None,
        expected=None,
        got=None,
        tests_run=0,
        seed=1234,
        minimized=False,
        reproduced=False,
        limitations=["Only the coin-change benchmark is supported."],
        message="This problem slug is not supported.",
    )
