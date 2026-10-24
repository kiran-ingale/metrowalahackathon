from fastapi import APIRouter, Request

from app.models.requests import CounterexampleRequest
from app.models.responses import CounterexampleResponse
from app.services.counterexamples.service import CounterexampleService

router = APIRouter(prefix="/v1/counterexamples", tags=["counterexamples"])


def get_counterexample_service(request: Request) -> CounterexampleService:
    return request.app.state.counterexample_service


@router.post("/find", response_model=CounterexampleResponse)
def find_counterexample(
    payload: CounterexampleRequest, request: Request
) -> CounterexampleResponse:
    return get_counterexample_service(request).find(payload)
