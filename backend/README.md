# Unstuck Backend

## Prerequisites

- Python 3.11 or newer
- An OpenAI API key is only required when the real LLM client is implemented. Module 00 runs without one.

## Setup

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration

`backend/.env` holds local settings and is excluded from Git. Copy `.env.example` if
you need to recreate it. The real OpenAI client is introduced in Module 03, so
`OPENAI_API_KEY` can remain empty during Modules 00–02.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Server-only API key for the future OpenAI client |
| `OPENAI_MODEL` | Optional model selected by the future OpenAI client |
| `APP_ENV` | `development`, `test`, or `production` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `ALLOWED_ORIGINS` | Comma-separated allowed browser origins |
| `REQUEST_BODY_LIMIT_BYTES` | Maximum accepted request body size |

## Run locally

```powershell
uvicorn app.main:app --reload
```

Check the service at `http://127.0.0.1:8000/health`.

## Endpoint examples

The test suite uses a fixture client and requires no API key. A locally running
server returns a safe unavailable response for guidance until both `OPENAI_API_KEY`
and `OPENAI_MODEL` are configured. Requests carrying source code must stay local;
do not send candidate code to a public hosted deployment.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health

Invoke-RestMethod http://127.0.0.1:8000/v1/problems/house-robber/recommendations
```

Guidance requests use a `ProblemContext` with a title, statement, language, and
the relevant approach, code, or verdict. Counterexample search additionally
requires a Python `solve(input_data)` function and explicit `confirm_execution: true`.

## Available endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Service status and version |
| `GET` | `/v1/problems/{slug}` | Curated public problem metadata |
| `GET` | `/v1/problems/{slug}/recommendations` | Optional prerequisite and related-problem suggestions |
| `POST` | `/v1/guidance/hint` | Generate one requested progressive-hint level |
| `POST` | `/v1/guidance/validate` | Assess a pasted approach and its constraints |
| `POST` | `/v1/guidance/debug` | Explain a supplied verdict or error message |
| `POST` | `/v1/counterexamples/find` | Opt-in verified search for supported Python problems |

The initial catalog is local-only and validates at application startup. For example,
`/v1/problems/two-sum` returns its patterns, prerequisites, related problems, and
constraints without exposing internal counterexample implementation details.

Recommendation query parameters are optional and repeatable: `solved_slug`,
`dismissed_slug`, and `weak_pattern`. They are supplied from local extension data;
recommendations never prevent a learner from attempting the current problem.

Guidance endpoints use the fixture client until both `OPENAI_API_KEY` and
`OPENAI_MODEL` are configured. Responses that cannot be validated return a stable,
retryable API error instead of raw provider output.

## Local counterexample runner

The internal runner supports only a Python function with this contract:

```python
def solve(input_data):
    return json_serializable_result
```

It executes one call in a new temporary directory with a sanitized environment,
short timeout, and capped captured output. It is deliberately not exposed as a
public API. This is **local-MVP isolation**, not a production sandbox: a public
deployment must use host-enforced container or VM isolation. On Windows, this
runner does not apply per-process CPU or memory limits.

`POST /v1/counterexamples/find` currently supports only the curated Python Two Sum
adapter. It requires `confirm_execution: true`, then runs a bounded search using a
recorded seed. A `found` response has been rerun after shrinking; `none_found`
means only that the bounded search found no mismatch, not that a submission is correct.

Counterexample response states have these meanings:

| State | Meaning |
| --- | --- |
| `found` | A minimized mismatch was reproduced against the trusted oracle. |
| `none_found` | No mismatch appeared in the bounded deterministic cases; this is not proof of correctness. |
| `not_supported` | The language or problem has no hand-authored adapter, so code was not run. |
| `could_not_verify` | The candidate, oracle, or final reproduction could not complete reliably. |

## Quality checks

```powershell
ruff check .
python -m pip check
pytest -q
pytest -m counterexample_eval -q
```

Dependencies are pinned in `requirements.txt`. The most recent static dependency
review ran on 2026-10-24 with `python -m pip check`; it completed without conflicts.

## Release checklist

- [x] `ruff check .`, `python -m pip check`, and the fixture-based pytest suite pass locally.
- [x] Tests use only the fixture LLM client and local catalog; no live LLM or LeetCode page is called.
- [x] Health, guidance, recommendations, and verified Two Sum counterexample flows have automated smoke coverage.
- [x] Error logging records only request IDs and exception types, never source, prompts, journals, or secrets.
- [x] GitHub Actions runs lint, dependency checks, and tests on backend changes.
- [ ] Before a live demo, configure only the required local `OPENAI_API_KEY` and `OPENAI_MODEL` values.
