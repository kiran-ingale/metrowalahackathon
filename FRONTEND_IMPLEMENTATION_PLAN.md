# Unstuck Frontend: Two-Hour Hackathon Plan

This is a demo-first plan for the next two hours. Build one polished, useful learner flow: enter a coding problem, ask for a gentle hint, and see a clear response. Keep the interface cute and cozy through color, warmth, and small details; keep the implementation small enough to finish.

## The two-hour finish line

At the end of 120 minutes, a user can open Unstuck, enter a problem and their current thinking, choose **Get a hint**, and see a readable response. The page works even if the backend is unavailable by showing a clearly labeled demo response. It looks good at laptop and narrow side-panel widths.

## Scope for this sprint

### Build now

- One responsive screen with a welcoming header, problem form, action button, and answer card.
- Inputs for problem title, problem statement, and optional approach/code. Keep the first view short; put optional details behind a disclosure if needed.
- One working action: **Get a hint**. If the API already supports another action reliably, add **Check my approach** as the only second action.
- Loading, success, empty-input, and backend-error states.
- A small, clearly labeled local demo response when no backend is configured, so the experience can be shown live.
- Temporary in-memory state only. Refresh persistence, extension packaging, and storage can wait.

### Defer until after the demo

- Chrome extension packaging, service worker, content scripts, and LeetCode extraction.
- Zustand, Dexie, IndexedDB, a database schema, and settings screens.
- Hint-history persistence, journal, recommendations, and local-data deletion.
- Counterexample execution, multiple guidance modes, authentication, and broad test infrastructure.
- Custom editor integration. A normal textarea is enough for the demo.

Use the project’s existing frontend stack if one exists. If starting from scratch, use the smallest working setup already available; avoid adding libraries unless a required feature cannot be built without them.

## Cozy visual direction

- Warm paper background (`#FAF6EF`), cream cards (`#FFFDF8`), dark cocoa text (`#3F332E`), muted sage accents (`#728B72`), and a restrained peach highlight (`#E9A98D`).
- Rounded cards and controls (12–18px), soft borders, generous spacing, and subtle shadows. Keep contrast strong and body text easy to read.
- Friendly, calm microcopy: “Let’s untangle this together” and “Start with a small nudge.” Avoid childish decorations or excessive emoji.
- Use one readable sans-serif font already available in the project. Add a small friendly icon or simple inline illustration only if it takes a few minutes; do not let decoration delay the core flow.
- On narrow layouts, stack everything in one column, keep the primary action visible, and avoid horizontal scrolling.

## Modules and approval checkpoints

Work through these modules in order. Each has a design approval before implementation and a separate approval before its test/debug pass. At the checkpoint, show the concrete screen or changes and summarize what will be tested. If approval is not given, pause that phase and do not move on to later modules. Keep each design discussion brief so the build can still fit the two-hour window.

| Module | Time | Deliverable | Design approval checkpoint | Test/debug approval checkpoint |
| --- | --- | --- | --- | --- |
| 0. Project check | 0–10 min | App run command, entry point, and actual backend route/contract identified. | Confirm the existing app and the smallest viable demo route. | After approval, start the app and resolve startup or integration blockers. |
| 1. Cozy visual shell | 10–30 min | Header, page background, card, type, colors, and responsive frame. | Show the proposed visual direction and get approval before implementing it. | After approval, inspect desktop and narrow layouts; fix visual issues. |
| 2. Problem form | 30–55 min | Editable title and statement, optional approach/code, and empty-input feedback. | Show the form layout and field labels for approval before building. | After approval, try empty, partial, and complete inputs; fix usability issues. |
| 3. Hint request | 55–85 min | One hint action connected to the real backend contract, with readable response. | Show the action and answer-card design for approval before wiring it up. | After approval, exercise a successful request and inspect request/error handling; debug failures. |
| 4. States and fallback | 85–100 min | Loading, retry, backend error, and clearly labeled demo response. | Show the state treatments and demo labeling for approval before implementation. | After approval, trigger each state and fix confusing or broken behavior. |
| 5. Final polish and demo | 100–120 min | Responsive polish and one complete demo path. | Show the final polish changes before applying any additional design adjustments. | After approval, walk through the full flow, fix only issues on that path, and prepare demo context. |

### Approval protocol

At each design checkpoint, present a concise proposal or screenshot/mockup and ask whether to proceed. After implementing the module, report what changed and ask permission to test and debug it. Once that approval arrives, run the relevant checks, fix issues in that module, and report the result before requesting approval for the next module’s design. Keep implementation and test/debug permissions separate as requested.

If the clock is tight, preserve Modules 0–3 and simplify visual polish or optional fields. Do not skip an approval gate; reduce the module scope instead.

### Current sprint notes

- The workspace has no frontend scaffold, Node/npm runtime, backend implementation, or concrete API request schema. The current demo is therefore dependency-free HTML, CSS, and JavaScript that can be opened directly as `index.html`.
- Modules 3 and 4 are combined for this workspace: the hint flow has loading, retry, and an explicit generic demo response. Real backend integration and its network error state are deferred until an endpoint contract exists.
- The demo response is generic and is not based on the problem statement. Keep that limitation visible in the interface.
- Structural and interaction checks can run here, but browser rendering inspection is unavailable because no browser is exposed to the UI tool.
- Modules 1–5 are implemented. Final form/demo interaction checks, HTML structure checks, responsive-rule checks, contrast checks, and `git diff --check` passed. Browser screenshot review remains unverified.

## Suggested single-screen layout

1. **Header:** Unstuck wordmark, a small “your coding companion” subtitle, and a warm greeting.
2. **Problem card:** Title and problem statement fields; optional “Add my approach or code” disclosure.
3. **Primary action:** “Get a hint” with one short reassurance that hints reveal gradually.
4. **Response card:** Loading indicator, then the hint with a small “Want another nudge?” follow-up only if the API supports another level. Never imply the response is verified if it is generated guidance.
5. **Footer note:** “Your work stays in this session” only if true; otherwise state the actual storage behavior.

## API and demo behavior

- Inspect the backend implementation before wiring requests; use its real route, request fields, and response fields. Do not build a speculative generic client.
- Keep API URL configuration in the project’s existing environment setup. Never put a provider secret in frontend code.
- Set a short request timeout and show a human-readable error with a retry button.
- If the backend is not ready, provide a deterministic sample response behind an obvious “Demo response” label. Do not silently present canned text as a live model result.
- Keep user context in memory for this sprint. Do not claim data is saved or private beyond what the implementation guarantees.

## Build order and cut line

Work in this order: app runs → polished static screen → editable problem form → one real hint request → clear loading/error/demo states → responsive polish. At minute 90, stop adding features and use the remaining time to make the main path presentable and reliable. If time runs short, omit the second action and optional approach/code fields before cutting the working hint flow.

## Demo acceptance checklist

- The app starts with the documented command and opens without a blank screen.
- A user can enter a title and statement, request a hint, and read the result.
- Empty input, loading, backend failure, and demo fallback are understandable.
- The cozy palette and spacing feel consistent, with readable contrast and keyboard focus.
- The layout fits a narrow panel without horizontal scrolling.
- The demo clearly distinguishes a live backend result from a canned fallback.

## Next pass after the hackathon

Once the demo flow is stable, add the next feature in this order: approach checking and debugging, the progressive hint ladder with saved history, local journal, extension side-panel integration, and finally optional LeetCode extraction. Add IndexedDB or a richer state layer only when those features need it.
