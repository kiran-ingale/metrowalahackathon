# Unstuck Implementation Plans

Unstuck's roadmap is split into three coordinated plans:

1. [Frontend implementation plan](FRONTEND_IMPLEMENTATION_PLAN.md) — Chrome extension, side panel experience, local storage, and LeetCode adapter.
2. [Backend implementation plan](BACKEND_IMPLEMENTATION_PLAN.md) — FastAPI services, LLM guidance, curated catalog, and counterexample engine.
3. [Verification and security implementation plan](VERIFICATION_SECURITY_IMPLEMENTATION_PLAN.md) — testing, evaluation, privacy, sandboxing, and release gates.

## Shared MVP Scope

The first release accepts manually pasted problem context, code, approach, and error output. It provides progressive hints, approach validation, guided debugging, verified counterexamples for supported Python problems, and a local coding journal.

Automatic LeetCode extraction, broad language support, hosted execution, synchronization, and advanced learning features follow only once the core learning loop proves useful.

## Integration Milestones

| Milestone | Frontend | Backend | Verification/security |
| --- | --- | --- | --- |
| M0 | Extension shell and typed API client | FastAPI health endpoint and settings | Tooling, schemas, and baseline checks |
| M1 | Hint ladder and context form | Structured hint service and catalog | Hint-policy and schema fixtures |
| M2 | Validation and debug panels | Guidance modes and error analysis | Classification and response tests |
| M3 | Counterexample display | Python oracle, runner, and shrinker | Sandbox tests and reproducibility gate |
| M4 | Journal and recommendations | Catalog recommendation endpoint | Local-data and user-flow tests |
| M5 | Isolated LeetCode adapter | Optional metadata support | DOM fixture tests and privacy review |

## Delivery Sequence

1. Complete M0–M2 for a paste-in, demoable learning loop.
2. Complete M3 before claiming verified approach feedback.
3. Complete M4 to establish learning continuity.
4. Add M5 only after the manual workflow is reliable.
