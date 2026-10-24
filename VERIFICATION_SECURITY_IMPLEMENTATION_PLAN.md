# Unstuck Verification and Security Implementation Plan

This plan ensures Unstuck's guidance is trustworthy, learner data is treated carefully, and executable counterexamples are not overstated or exposed unsafely.

## 1. Goals and Boundaries

### Goals

- Make it clear whether feedback is an AI assessment or an executed verification.
- Prevent unsafe handling of pasted code, API keys, journal entries, and LeetCode context.
- Establish tests and evaluation gates before expanding product scope.
- Keep the local MVP safe enough for development while explicitly excluding public hosted execution.

### Boundary

The MVP may run supported Python code only on the developer's or user's controlled local environment with restrictive limits. It is not an internet-facing arbitrary-code execution platform. Public execution requires a separately designed and reviewed sandbox.

## 2. Trust Labels in the Product

Every result shown to the learner must state its evidence level:

| Label | Meaning | UI requirement |
| --- | --- | --- |
| AI guidance | A model-generated explanation based on supplied context | Never call it tested or proven |
| Constraint assessment | Complexity compared with parsed or cataloged limits | Show assumptions and unknown constraints |
| Examples checked | A claim checked only against provided examples | Do not imply general correctness |
| Verified counterexample | Candidate and trusted oracle disagree on a reproduced input | Show input, expected, actual, and support scope |
| Could not verify | Oracle, runner, or contract did not support the request | Explain limitation and offer a safe next step |

This distinction is central to Unstuck's credibility. The interface and API must not blur these states.

## 3. Validation Layers

### Client input validation

- Limit problem-statement, code, error-message, and journal-field size.
- Validate language, verdict, hint level, and problem slug against enumerated values.
- Escape all rendered text and never inject pasted code or model output as HTML.
- Require explicit action before sending code or text to the backend.

### API validation

- Use strict Pydantic request/response schemas.
- Reject unknown or malformed values rather than coercing them silently.
- Apply request-body size limits, structured errors, and timeouts.
- Restrict CORS to approved extension origins.
- Keep server credentials in environment configuration only; never return them to the client.

### Model-output validation

- Use separate JSON schemas for hints, validation, debugging, and journal review.
- Parse and validate every response before presentation.
- Retry at most once for a schema-repair request.
- Reject output that violates the requested hint level or claims unperformed verification.
- Record schema failures as anonymous quality telemetry, not raw content.

### Catalog validation

- Validate problem IDs, referenced prerequisites, patterns, and related slugs at startup.
- Reject duplicate slugs and circular prerequisite graphs.
- Test all counterexample adapters against their official examples before release.

## 4. Counterexample Verification Protocol

### Preconditions

Counterexample search may proceed only when all conditions hold:

1. The selected problem has a hand-authored supported adapter.
2. The selected language has an approved runner.
3. The candidate code matches the documented function contract.
4. The oracle passes official sample tests in the current build.

Otherwise return `not_supported` or `could_not_verify` rather than an ungrounded verdict.

### Reproducible test process

1. Generate bounded input using a recorded deterministic seed.
2. Run candidate and oracle in isolated child processes.
3. Compare normalized JSON-compatible outputs.
4. On disagreement, shrink the input.
5. Rerun candidate and oracle on the shrunk input.
6. Report a counterexample only if the final run reproduces the mismatch.
7. Persist only non-sensitive diagnostic metadata needed for a local retry, never user code by default.

### Required result checks

- Oracle passes examples.
- Candidate result is captured with capped output.
- Timeout, exception, and invalid-output results are represented distinctly.
- Final minimized mismatch reproduces.
- Report contains the input, expected result, actual result, test count, and whether minimization succeeded.

## 5. Execution-Sandbox Safeguards

### Local MVP controls

- Create a dedicated process for each candidate and oracle execution.
- Use short wall-clock timeouts and CPU limits where supported.
- Apply memory caps where supported by the operating system.
- Use a fresh empty working directory.
- Clear inherited environment variables and never expose secrets.
- Disable network access where the platform supports it.
- Cap standard output, standard error, input size, and test-case count.
- Ensure the parent backend process never executes user source directly.
- Fail closed for unsupported operating systems, language runtimes, and contracts.

### Before public execution

Do not publish hosted execution until all of the following are complete:

1. Use a container or dedicated isolation technology such as `nsjail` or gVisor.
2. Isolate the runner from API, database, and credential-bearing processes.
3. Run containers without network access, writable host mounts, elevated capabilities, or privileged mode.
4. Enforce CPU, memory, process-count, file-size, and wall-time quotas.
5. Add job queues, rate limits, audit logs, incident handling, and independent security review.
6. Threat-model escape paths, data exfiltration, denial of service, and dependency compromise.

## 6. Privacy Plan

### Defaults

- Journal entries, hints seen, settings, and local history stay in IndexedDB by default.
- Send code, approach text, and error messages only after a learner takes a specific action.
- Do not collect LeetCode profile history in the MVP.
- Do not log raw code, full journal text, model prompts, or API keys.
- Provide a clear local-data deletion control before public testing.

### User-facing disclosure

The extension should clearly say:

1. What data is in the current request.
2. Whether the action is local-only or sent to the backend.
3. What remains on the device.
4. Whether code execution is available, unsupported, or could not be verified.

## 7. Test Strategy

### Unit tests

- Request/response models and frontend runtime parsers.
- Catalog validation and prerequisite graph rules.
- Generator bounds, oracle correctness, normalization, and shrinkers.
- Timeout, memory-limit, invalid-output, exception, and unsupported-runner behavior.
- Hint-level policy checks and response classification.

### Integration tests

- Endpoint behavior with a deterministic fixture LLM.
- Extension API client behavior against malformed and failed responses.
- Full runner flow with known-correct and known-wrong candidates.
- Local persistence and delete-all-data behavior.
- LeetCode adapter fixture HTML with high, partial, and unavailable extraction.

### End-to-end smoke test

1. Paste a supported Two Sum problem context and flawed Python candidate.
2. Request a Level 1 hint and verify no full solution appears.
3. Validate the approach and verify the feedback label is not “verified.”
4. Run counterexample search and ensure a reproducible failing case renders expected and actual output.
5. Save and retrieve a journal entry.
6. Simulate backend failure and verify the panel remains usable.

## 8. Evaluation Set

Build an internal set of at least 20 cataloged problems. For each, include:

- Official examples and verified oracle.
- A valid brute-force solution.
- A valid efficient solution.
- A fundamentally incorrect solution with a known minimal failing input.
- A correct-but-too-slow solution when meaningful.
- Expected classification and expected verification state.

Track these release metrics:

| Metric | MVP release threshold |
| --- | --- |
| Structured response validity | At least 95% parse without manual repair |
| Level 1–3 hint compliance | No unsolicited complete-code responses in sampled set |
| Approach classification | Correct category for seeded valid, inefficient, and flawed cases |
| Counterexample precision | 100% of reported cases reproduce in the oracle harness |
| Counterexample clarity | Every result includes input, expected, actual, and limitations |
| Failure resilience | UI has a usable state for backend, adapter, and verification failures |

Classify every evaluation failure as catalog defect, missing user context, prompt defect, model reasoning, schema defect, oracle defect, runner defect, or UI defect. Repair the responsible layer, not only the individual example.

## 9. Release Gates

### Internal demo gate

- Manual paste-in flow works without browser-page extraction.
- Hints remain user-controlled and no level auto-escalates.
- UI labels guidance and verification accurately.
- At least three supported counterexample adapters reproduce seeded bugs.
- No raw code or API keys appear in logs.

### Private beta gate

- 20-problem evaluation set meets defined quality thresholds.
- Local-data disclosure and deletion controls are complete.
- Adapter degrades cleanly to manual input.
- Request limits, CORS restrictions, and error handling are tested.
- Security review confirms no public arbitrary-code execution path.

### Public execution gate

- Hardened sandbox design and implementation are independently reviewed.
- Isolation, limits, rate limits, monitoring, and incident response are operational.
- Threat model is documented and tested against realistic abuse cases.
- Privacy terms and user disclosures match actual data flows.

## 10. Ongoing Checks

- Run lint, type checks, unit tests, and fixture-based integration tests on every change.
- Run the counterexample evaluation harness when runner, oracle, generator, or shrinker code changes.
- Review a sampled set of production-like guidance responses when prompts or model configurations change.
- Re-check the LeetCode adapter against saved fixtures after any target-site layout update.
- Revisit the threat model before enabling a new language, persistence layer, external integration, or hosting mode.
