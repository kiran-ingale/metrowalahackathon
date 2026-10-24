# Unstuck Frontend Implementation Plan

This plan covers the Chrome extension that presents Unstuck inside the learner's workflow. It prioritizes a reliable manual paste-in experience, then adds optional LeetCode context extraction.

## 1. Frontend Scope

### MVP responsibilities

- Collect problem context, code, approach text, and verdict/error details.
- Present explicit actions: **Hint**, **Check my approach**, **Explain error**, and **Break my code**.
- Render guidance without unsolicited complete code.
- Persist hints, journal entries, and settings locally.
- Make verification status and limitations understandable.

### Exclusions

- Auto-submitting or editing LeetCode code.
- Direct use of an LLM key in the extension.
- Mandatory profile scraping or account-history collection.
- Cloud synchronization of journal data.

## 2. Technical Foundation

| Area | Choice | Reason |
| --- | --- | --- |
| Platform | Chrome Extension Manifest V3 | Side panel support and modern extension lifecycle |
| Language | TypeScript | Reliable contracts with the backend and adapter |
| UI | React + Tailwind CSS | Fast, reusable side-panel components |
| Build | Vite + CRXJS | Extension-focused local development and builds |
| Ephemeral state | Zustand | Compact request and UI state |
| Persistent state | Dexie over IndexedDB | Local-first journals, hint history, and settings |
| Tests | Vitest + Testing Library | Fast component, state, and API-client tests |

Suggested structure:

```text
extension/
├── src/
│   ├── background/
│   │   └── service-worker.ts
│   ├── content/
│   │   └── leetcode-content.ts
│   ├── sidepanel/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── features/
│   │   └── styles/
│   ├── adapters/
│   │   └── leetcode-adapter.ts
│   └── shared/
│       ├── api-client.ts
│       ├── contracts.ts
│       ├── db.ts
│       ├── stores.ts
│       └── validation.ts
├── tests/
├── manifest.config.ts
└── package.json
```

## 3. Shared Contracts

Build frontend types from a single backend-compatible schema. At minimum, model `ProblemContext`, `HintResponse`, `ApproachFeedback`, `CounterexampleResponse`, and `JournalEntry`.

`ProblemContext` should contain:

- Problem title, optional slug, statement, examples, and constraints.
- Selected language and optionally pasted code.
- Optional plain-language approach.
- Optional verdict and raw error message.

Use a discriminated API-result type for every backend action:

```ts
type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; code: string; message: string; retryable: boolean };
```

Do not render raw server or model content until it passes local runtime validation.

## 4. Milestone M0: Extension Shell

1. Scaffold Vite, CRXJS, React, TypeScript, Tailwind, Zustand, Dexie, Vitest, and Testing Library.
2. Register the Manifest V3 service worker, content script, and side panel.
3. Build a minimal side panel with service health and backend connection indicators.
4. Add a typed API client with timeout, JSON parsing, and recoverable error states.
5. Create a Dexie database with `settings`, `attempts`, `hintsSeen`, and `journal` tables.
6. Configure local development against a backend URL in an extension-specific environment variable.

**Exit criteria:** Loading the unpacked extension opens the panel, confirms backend health, and shows a helpful unavailable-backend state.

## 5. Milestone M1: Context and Hint Ladder

### Context form

Build a paste-in form with:

- Problem title and full statement.
- Examples and constraints.
- Language selector.
- Code editor or multiline code field.
- Plain-language approach field.
- Verdict selector and error message field.

Keep every field editable, including later auto-detected values. A user must be able to correct incomplete page extraction.

### Hint ladder

1. Display four levels: Nudge, Direction, Strategy, and Walkthrough.
2. Request only the level the user selects.
3. Persist each revealed level against the current attempt.
4. Show a concise warning before Level 4 that it may include pseudocode or a trace.
5. Do not automatically request or show the next level.
6. Add a separate explicit action for complete code only if this is approved as a product feature later.

**Exit criteria:** A user can provide a context, request Level 1, deliberately escalate, reload the panel, and see which levels they already opened.

## 6. Milestone M2: Feedback Workspace

### Action bar

Place four primary actions near the current context:

- **Hint** opens/selects the hint ladder.
- **Check my approach** sends code and/or reasoning for validation.
- **Explain error** sends the actual verdict and error detail.
- **Break my code** starts counterexample search only after the user opts in.

### Result components

Implement separate components rather than one generic AI-response area:

| Component | Required content |
| --- | --- |
| Approach feedback | Status, reasoning, time/space complexity, constraint assessment, one next question |
| Debug feedback | Actual result interpreted, likely cause, relevant edge case, next debugging step |
| Counterexample | Input, expected output, actual output, minimized indicator, verification status |
| Verification note | Clear explanation of `found`, `none_found`, `not_supported`, or `could_not_verify` |

Never label an AI-only conclusion as verified. The UI must distinguish a model assessment from an executed mismatch.

**Exit criteria:** Each action has loading, success, empty, unavailable, and retry states; response content remains readable at the narrow side-panel width.

## 7. Milestone M4: Journal and Recommendations

### Journal

After an accepted result or a manual **Reflect** action, show a low-friction sheet with four prompts:

1. Which approach did you use?
2. What was your reasoning?
3. What obstacle or mistake did you face?
4. What will you remember next time?

Persist entries in IndexedDB. Allow save, edit, skip, and return later. Do not block a learner from continuing if they skip reflection.

### Recommendation card

Show at most two next problems:

- One prerequisite or reinforcement exercise.
- One adjacent problem sharing the current pattern.

Each item should show difficulty, patterns, and a short explanation of its relevance. A dismissed recommendation should not resurface immediately.

**Exit criteria:** Journal entries survive extension restart; recommendation display gracefully handles absent catalog data.

## 8. Milestone M5: LeetCode Adapter

Keep all site-specific DOM code in `src/adapters/leetcode-adapter.ts`.

```ts
type AdapterResult = {
  context: Partial<ProblemContext>;
  confidence: "high" | "partial" | "unavailable";
  missingFields: string[];
};
```

Implementation sequence:

1. Detect supported LeetCode problem URLs.
2. Extract title, slug, statement, visible examples, constraints, and visible verdict.
3. Read Monaco editor contents only when available through user-visible page state.
4. Send normalized data to the side panel through the service worker.
5. Display extraction confidence and retain manual edit controls.
6. Fall back completely to paste-in when selectors fail.

The adapter must never throw because a selector is absent. Do not auto-submit code, call private endpoints, or collect profile data in the MVP.

## 9. Local State Model

| Data | Store | Retention |
| --- | --- | --- |
| Active context and request state | Zustand | Current panel session |
| Hint levels already viewed | Dexie `hintsSeen` | Per attempt |
| Preferences and optional hint budget | Dexie `settings` | Until reset |
| Journal entries | Dexie `journal` | Until user deletes them |
| Recommendation dismissals | Dexie `settings` or dedicated table | Time-bounded |
| Catalog cache | Dexie | Versioned and replaceable |

Provide a local-data settings screen before public testing. It must explain what stays on device and offer a confirmed `Delete all local data` action.

## 10. Testing and Acceptance

- Component-test hint escalation, Level 4 confirmation, loading, retry, and unavailable states.
- Test the API client against successful, malformed, timeout, and non-JSON responses.
- Test Zustand and Dexie behavior for attempt resets, hint persistence, journal CRUD, and local-data deletion.
- Test the adapter with saved HTML fixtures, never a live LeetCode page in CI.
- Add an end-to-end smoke test: paste a Two Sum context, request a hint, validate an approach, and display a seeded counterexample.

## 11. Frontend Build Order

1. Extension shell, shared contracts, API client, and local database.
2. Manual context form and side-panel layout.
3. Hint ladder and persisted hint history.
4. Approach/debug result cards.
5. Counterexample result card.
6. Journal and recommendation card.
7. Adapter and extraction confidence UI.

Complete the manual workflow before attempting DOM extraction. The product must remain useful when the target website changes.
