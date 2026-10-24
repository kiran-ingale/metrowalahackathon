# Unstuck Complete Project Integration Plan

## Product rule

Build the project described in `README.md`: a hint-first LeetCode learning companion that helps users reason independently. Every module must preserve these rules:

- Offer the smallest useful hint first. Escalate only when the user asks; never reveal later hint levels automatically.
- Judge the learner's approach on its merits. Never punish a different valid solution.
- Claim an approach is wrong only when a counterexample has been reproduced against a trusted oracle. Otherwise say that it could not be verified.
- Keep recommendations optional, user work local by default, and any code execution explicitly confirmed and isolated.
- Read from LeetCode only. Never auto-submit, mutate a submission, or depend on private endpoints.

## Current integration state

- `index.html`, `styles.css`, and `script.js` implement a cozy paste-in demo form. The page calls the backend for live, user-requested hint levels 1–4 and shows an explicitly labeled generic hint only when the service is unavailable.
- `backend/` contains the main FastAPI application: guidance, catalog, recommendations, and a curated Python counterexample path.
- `verifier/` now contains internal execution, comparison, shrinking, and adapter utilities only. Its separate FastAPI route was removed because it returned a canned coin-change result without running submitted code. The backend is the only public HTTP API.
- The README calls for a Manifest V3 TypeScript/React side panel, hint ladder, approach/debug actions, counterexample flow, local journal, and curated prerequisite path. There is currently no `extension/` directory.
- There is no packaged extension yet. The root README now documents how to run the current local web demo rather than pointing to an absent `/extension` directory.
- Backend and verifier suites pass: backend `74 passed`; verifier internal tests `14 passed`. The backend emitted one Starlette/AnyIO deprecation warning. The live hint endpoint was exercised with the configured model and returned a valid Level 1 response. CORS preflight from `http://localhost:5173` passed. A test helper's 0.2-second execution timeout was too low for a fresh Windows child interpreter, so it now allows 1.5 seconds; the production runner's configured limit is unchanged.
- `styles.css` has one uncommitted local fix (`.hint-loading[hidden] { display: none; }`). Preserve it during integration and keep it separate from project merge work until intentionally committed.

## Integration choice

Use `backend/` as the public API and contract owner. Keep one counterexample request/response contract at `/v1/counterexamples/find`. The separate verifier API was retired because its canned coin-change result did not execute submitted code; reusable execution utilities remain internal and its tests exercise actual candidate code. The broader runner and adapter reconciliation remains Module 4 work. Do not have a client call two services or present canned output as execution evidence.

Use the README's local-first principle for extension history and journal. The backend receives only the problem context needed for a request and code only after the user chooses an action that needs it. Keep provider credentials on the backend.

## Modules and gates

Complete the module's implementation, run its listed checks, debug failures, and record the result before moving to the next module. For any new interface or consequential product behavior, show a concrete proposal and get design approval before implementing that part. Test/debug approval already requested for each module is treated as granted by the user's current request.

| Module | Scope and deliverable | Test/debug gate (must pass before next module) |
| --- | --- | --- |
| 0. Product and API contract | **Complete.** Backend is the canonical public API. Removed the verifier's fake public endpoint; retained its execution utilities internally. Added backend HTTP contract tests for consent, reproduced mismatches, and absence of the retired route. | **Pass:** backend `74 passed`; verifier internal suite `14 passed`; `git diff --check` passed. |
| 1. Extension shell | **MVP shell added.** Added a Manifest V3 side panel in `extension/`, using the approved cozy UI and a fixed-origin service-worker bridge to the local backend. Requests only `sidePanel` and the local backend host. | **Package checks pass:** manifest JSON, referenced assets, and service-worker message path validate. Chrome is unavailable in this environment, so loading the unpacked folder and visual side-panel smoke test remain to be run in Chrome. |
| 2. Problem context and hint ladder | **MVP hint flow integrated.** The side panel sends title/statement and optional approach/code only after the user requests a hint; levels are escalated only by button; API failures show a labeled generic demo response. | **API checks pass:** live Level 1 response, CORS-independent service-worker host permission path, backend/verifier tests. Full click-through in Chrome remains pending because no browser surface is available here. |
| 3. Approach validation and guided debugging | Connect **Check my approach** and **Explain error** to their backend routes. Include constraints, pasted approach/code, verdict, and error as appropriate. Describe valid-but-inefficient separately from flawed. | Test valid, inefficient, flawed, insufficient-context, compile/runtime, wrong-answer, and TLE paths. Confirm no unsupported “wrong” claim and that errors do not echo unsafe provider details. |
| 4. Verified counterexample engine | Reconcile `backend/app/services/counterexamples/` and `verifier/`. Retain trusted hand-authored oracles/adapters, bounded generated inputs, execution limits, shrinking, and final reproduction. Surface input/expected/actual plus seed and honest status. Require explicit execution consent. | Run deterministic golden cases, known-wrong and known-correct candidates, shrinking/reproduction checks, timeout/output limits, unsupported languages/problems, missing consent, and Windows/platform limitations. Any failure blocks integration. |
| 5. Curated catalog and optional recommendations | Connect problem metadata and prerequisite/pattern suggestions. Start from the small verified catalog; suggestions never gate the current problem. Add user solved/dismissed/weak-pattern context only from local extension state. | Test known/unknown slugs, prerequisite graph integrity, deterministic recommendation order, dismissed/solved filtering, and that suggestions never block the user. |
| 6. Local learning record | Add local IndexedDB storage for hint history, attempts, and a short reflection journal. Keep delete-all and clear privacy copy. Add review endpoint only after the local data model and disclosure are approved. | Test create/read/update/delete, reload persistence, migration, empty/error states, deletion, and that journal/code are not sent unless the user explicitly starts a relevant backend action. |
| 7. LeetCode adapter | Add one isolated content-script adapter for problem text, examples, constraints, language, editor contents, and verdict. Fill the existing paste-in workflow when detection is unavailable. Read only; no submission controls or private APIs. | Fixture tests for supported/changed DOM, missing fields, multiple editors, stale page content, and permission boundaries. Confirm manual paste still works without the adapter. |
| 8. Quality, privacy, and demo release | Add extension checks to CI alongside backend checks; lint/build/test commands; local setup; demo configuration; and feature-status docs that match shipped behavior. Harden execution before any public deployment. | Run all backend, verifier/merged-runner, extension, contract, and packaging checks from a clean setup. Review data flows, secret handling, permission list, and demo claims against README. |

## Delivery order and scope cuts

For the README's core MVP, deliver Modules 0–4 first: side panel, hint ladder, approach/error guidance, and verified counterexamples. Module 5 improves the learning path; Module 6 completes the local-first journal pillar; Module 7 adds LeetCode convenience after paste-in works. Do not add extra features from the README's “beyond the core idea” list until the three pillars work end-to-end.

Treat a module as complete only when its acceptance checks pass and any failure has been fixed or written down as an explicit blocker. A passing unit suite alone does not prove the user journey: finish by walking through problem context → level 1 hint → user-requested escalation → approach check → verified counterexample or honest uncertainty → local reflection.

## Current demo scope

The time-boxed demo currently covers paste-in problem context and live progressive hints through the Chrome side panel and backend. Its generic fallback is labeled and used only when the backend cannot provide a response. Approach/debug actions, journal, LeetCode adapter, and full counterexample UI remain follow-up modules; do not describe them as shipped features.
