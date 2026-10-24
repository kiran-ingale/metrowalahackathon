# Unstuck Backend Implementation Plan

This plan covers the FastAPI backend that delivers structured guidance, curated problem metadata, and verified counterexamples. It assumes the extension is the primary client and keeps journals local during the MVP.

## 1. Backend Scope

### MVP responsibilities

- Serve versioned health and guidance APIs.
- Generate structured progressive hints, approach feedback, and debugging guidance.
- Provide curated problem and recommendation metadata.
- Run verified counterexample searches for a narrow set of supported Python problem contracts.
- Validate all client inputs and LLM outputs.

### Exclusions

- User accounts, cloud journal storage, and multi-device synchronization.
- A generic execution service for arbitrary LeetCode code.
- Runtime support for all languages.
- Unbounded LLM prompts or public production-scale execution.

## 2. Suggested Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── routes_health.py
│   │   ├── routes_guidance.py
│   │   ├── routes_problems.py
│   │   └── routes_counterexamples.py
│   ├── models/
│   │   ├── requests.py
│   │   └── responses.py
│   ├── services/
│   │   ├── guidance.py
│   │   ├── llm_client.py
│   │   ├── problem_catalog.py
│   │   ├── recommendations.py
│   │   └── counterexamples/
│   │       ├── runner.py
│   │       ├── oracles.py
│   │       ├── generators.py
│   │       └── shrinker.py
│   └── prompts/
│       ├── hint.md
│       ├── validate.md
│       ├── debug.md
│       └── journal_review.md
├── data/problems.json
├── tests/
├── requirements.txt
└── pyproject.toml
```

## 3. Foundation: M0

1. Create the FastAPI app with `GET /health` returning service name, version, and status.
2. Add Pydantic settings for LLM configuration, allowed CORS origins, request limits, and environment.
3. Configure CORS strictly for the development extension origin; do not use a wildcard production policy.
4. Add request IDs, structured error responses, and privacy-safe logs.
5. Add Ruff, pytest, and a fixture LLM client for deterministic local development.
6. Create CI steps for linting, type checks, and test execution.

**Exit criteria:** A local backend starts with documented commands; `/health` returns a versioned response; tests do not require a real LLM key.

## 4. API Contracts

Expose versioned endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness and version |
| `POST` | `/v1/guidance/hint` | Generate a requested hint level |
| `POST` | `/v1/guidance/validate` | Assess correctness and feasibility |
| `POST` | `/v1/guidance/debug` | Explain supplied verdict/error context |
| `POST` | `/v1/counterexamples/find` | Find a verified mismatch for a supported contract |
| `GET` | `/v1/problems/{slug}` | Return curated problem metadata |
| `GET` | `/v1/problems/{slug}/recommendations` | Return prerequisite and related exercises |

Shared request models must include a bounded `ProblemContext`: title, optional slug, statement, examples, constraints, language, optional code/approach, and optional verdict/error message.

Response models must be strict Pydantic schemas. Return a consistent error object containing a stable code, safe message, request ID, and retryability indicator.

## 5. Curated Problem Catalog: M1

Start with 30–50 hand-checked problems. Prioritize representative patterns rather than breadth:

- Arrays and hash maps
- Two pointers and sliding window
- Binary search and stacks
- Linked lists and trees
- Heaps and graphs
- Introductory dynamic programming

Each entry includes slug, title, difficulty, patterns, prerequisites, related slugs, constraints, and counterexample support status. Validate the entire JSON catalog on backend startup; reject duplicate slugs, missing related items, circular prerequisite chains, and invalid pattern names.

Use catalog facts as grounding context for the LLM. The catalog remains the source of truth for recommendations during the MVP.

## 6. Guidance Engine: M1–M2

### Orchestration flow

1. Validate and normalize incoming context.
2. Look up catalog facts by slug when present.
3. Select the specific guidance mode and response schema.
4. Construct a bounded prompt with the relevant constraints, code, approach, verdict, and prior hint levels.
5. Invoke the LLM client.
6. Parse and validate structured output.
7. Retry once with a repair prompt when the output is malformed.
8. Return a safe error if validation still fails.

### Mode requirements

| Mode | Requirements |
| --- | --- |
| Hint | Match the requested level and avoid complete code unless separately, explicitly authorized |
| Validate | Classify valid, valid-but-inefficient, fundamentally flawed, or insufficient context |
| Debug | Reason from actual error/verdict; do not invent a failure type |
| Journal review | Suggest corrections without replacing the learner's voice |

The validator must distinguish correctness from optimality. A working `O(n²)` approach is valid even if constraints make it impractical.

## 7. LLM Client Design

1. Define an `LLMClient` interface used only by the guidance service.
2. Provide a production implementation with server-only credentials.
3. Provide a deterministic fixture implementation for tests, demos, and frontend development.
4. Use per-mode timeouts, token budgets, and retry policies.
5. Set hard length limits for statement, code, error, and journal inputs.
6. Emit privacy-safe telemetry: mode, latency, model status, response-schema outcome, and request size bucket.

Never pass LLM output directly to the client if it fails schema or policy validation.

## 8. Counterexample Engine: M3

### First-version limitations

Support only a curated set of Python problems with hand-authored encoders, input generators, brute-force oracles, and shrinkers. Do not dynamically trust LLM-generated oracles.

Require a narrow callable contract:

```python
def solve(input_data):
    # Return a JSON-serializable result.
    ...
```

### Execution flow

1. Confirm that the problem slug and language are supported.
2. Verify the selected oracle on the problem's official examples.
3. Parse and validate the candidate code against the callable contract.
4. Generate deterministic, bounded small inputs from a recorded seed.
5. Run the candidate and oracle in separate restricted child processes.
6. Stop at the first reproducible mismatch.
7. Minimize the input with a problem-specific shrinker or generic delta debugging.
8. Rerun the minimized case to prove it still mismatches.
9. Return `found`, `none_found`, `not_supported`, or `could_not_verify` with clear evidence.

No counterexample result is valid until the final minimized mismatch has been reproduced.

## 9. Recommendations: M4

Return at most two recommendations for an MVP request:

1. One prerequisite or reinforcement problem at or below the current difficulty.
2. One nearby problem that shares the primary pattern.

Attach a short, catalog-derived explanation. Avoid recommending an item in a supplied dismissal or recent-history list. Treat recommendations as suggestions, never blockers.

## 10. Backend Build Order

1. FastAPI shell, configuration, models, fixture LLM, and `/health`.
2. Catalog loader/validator and problem metadata endpoint.
3. Hint service with strict structured output.
4. Approach validator and debug service.
5. Recommendation service.
6. Python execution contract, first oracle, generator, and runner.
7. Deterministic search and shrinking; add more hand-authored problem adapters.
8. Evaluation suite and observability polish.

## 11. Backend Acceptance Criteria

- Every endpoint has valid and invalid request tests.
- The fixture client supports local development without external credentials.
- Hint levels 1–3 never return unsolicited solution code in sampled evaluations.
- Valid brute-force, valid efficient, flawed, and too-slow seeded solutions classify correctly.
- Every counterexample returned by the API is independently reproducible.
- Unsupported execution cases fail closed with an explicit status.
