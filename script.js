const API_BASE_URL = "http://127.0.0.1:8000";

const form = document.querySelector("#problem-form");
const titleField = document.querySelector("#problem-title");
const statementField = document.querySelector("#problem-statement");
const approachField = document.querySelector("#approach");
const codeField = document.querySelector("#code");
const hintButton = document.querySelector(".hint-button");
const hintButtonLabel = document.querySelector(".hint-label");
const resultCard = document.querySelector("#hint-result");
const responseBadge = document.querySelector("#response-badge");
const responseNote = document.querySelector("#response-note");
const hintHeading = document.querySelector("#hint-heading");
const hintLoading = document.querySelector("#hint-loading");
const loadingCopy = document.querySelector("#loading-copy");
const hintAnswer = document.querySelector("#hint-answer");
const hintCopy = document.querySelector("#hint-copy");
const hintQuestion = document.querySelector("#hint-question");
const demoDisclaimer = document.querySelector("#demo-disclaimer");
const retryButton = document.querySelector("#retry-hint");
const nextHintButton = document.querySelector("#next-hint");
let shownLevels = [];
let currentLevel = 0;
let pendingRequest;
let activeController;

const requiredFields = [
  { input: titleField, error: document.querySelector("#title-error"), message: "Add a title so we know which problem you’re working on." },
  { input: statementField, error: document.querySelector("#statement-error"), message: "Paste the problem statement so we can give you a useful nudge." },
];

const demoHints = [
  "Before coding, work through the smallest example by hand. What does the input give you, and exactly what should the answer return?",
  "Look for the information you need to remember between steps. What small piece of state would help you make the next decision?",
  "Write down an invariant: what must stay true after each step? Trace one ordinary case and one edge case against it.",
  "Try explaining the steps in plain language first. Trace the smallest case, a repeated-value case, and a boundary case before turning those steps into code.",
];

async function requestBackendHint(payload, signal) {
  if (location.protocol === "chrome-extension:" && globalThis.chrome?.runtime?.sendMessage) {
    const result = await globalThis.chrome.runtime.sendMessage({
      type: "UNSTUCK_REQUEST_HINT",
      payload,
    });
    if (!result?.ok) throw new Error("The guidance service is unavailable.");
    return { ok: true, json: async () => result.payload };
  }

  return fetch(`${API_BASE_URL}/v1/guidance/hint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

function clearFieldError(field) {
  field.input.removeAttribute("aria-invalid");
  field.error.textContent = "";
}

function setBusy(isBusy, message = "Finding your first small step…") {
  resultCard.hidden = false;
  resultCard.setAttribute("aria-busy", String(isBusy));
  hintLoading.hidden = !isBusy;
  loadingCopy.textContent = message;
  hintAnswer.hidden = isBusy;
  hintButton.disabled = isBusy;
  retryButton.disabled = isBusy;
  nextHintButton.disabled = isBusy;
  if (isBusy) {
    retryButton.hidden = true;
    nextHintButton.hidden = true;
    hintQuestion.hidden = true;
  }
}

function showResponse(level, response, isDemo) {
  currentLevel = level;
  if (!shownLevels.includes(level)) shownLevels.push(level);
  responseBadge.hidden = !isDemo;
  responseNote.textContent = isDemo
    ? "Live guidance is unavailable · showing a generic sample"
    : `Level ${level} of 4 · generated from your problem`;
  hintHeading.textContent = response.title || `A gentle nudge · Level ${level}`;
  hintCopy.textContent = response.guidance;
  hintQuestion.textContent = response.question || "";
  hintQuestion.hidden = !response.question;
  demoDisclaimer.hidden = !isDemo;
  hintAnswer.hidden = false;
  hintLoading.hidden = true;
  resultCard.setAttribute("aria-busy", "false");
  retryButton.hidden = false;
  retryButton.disabled = false;
  nextHintButton.hidden = level >= 4;
  nextHintButton.disabled = false;
  nextHintButton.innerHTML = level === 3
    ? 'Ask for the final walkthrough <span aria-hidden="true">→</span>'
    : 'Ask for the next hint <span aria-hidden="true">→</span>';
  hintButton.disabled = false;
  hintButtonLabel.textContent = "Start over · Level 1";
}

function showDemoHint(level) {
  showResponse(level, {
    title: `A gentle nudge · Level ${level}`,
    guidance: demoHints[level - 1],
  }, true);
}

async function requestHint(level) {
  clearTimeout(pendingRequest);
  activeController?.abort();
  const controller = new AbortController();
  activeController = controller;
  pendingRequest = setTimeout(() => controller.abort(), 12000);
  setBusy(true, level === 1 ? "Finding your first small step…" : "Preparing the next hint you asked for…");
  hintButtonLabel.textContent = "Thinking…";

  const context = {
    title: titleField.value.trim(),
    statement: statementField.value.trim(),
    language: "python",
    approach: approachField.value.trim() || null,
    code: codeField.value.trim() || null,
  };

  try {
    const response = await requestBackendHint(
      { context, level, previous_hint_levels: shownLevels },
      controller.signal,
    );
    if (!response.ok) throw new Error(`Guidance service returned ${response.status}`);
    const payload = await response.json();
    if (activeController !== controller) return;
    if (payload.level !== level || payload.full_solution_included !== false || !payload.guidance) {
      throw new Error("The response did not match the requested hint level.");
    }
    showResponse(level, payload, false);
  } catch {
    if (activeController !== controller) return;
    showDemoHint(level);
  } finally {
    clearTimeout(pendingRequest);
    if (activeController === controller) activeController = null;
  }
}

function resetHints() {
  clearTimeout(pendingRequest);
  activeController?.abort();
  activeController = null;
  currentLevel = 0;
  shownLevels = [];
  resultCard.hidden = true;
  resultCard.setAttribute("aria-busy", "false");
  hintButton.disabled = false;
  hintButtonLabel.textContent = "Get a hint";
}

requiredFields.forEach((field) => {
  field.input.addEventListener("input", () => {
    clearFieldError(field);
    resetHints();
  });
});

[approachField, codeField].forEach((field) => {
  field.addEventListener("input", resetHints);
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  let firstInvalid = null;
  requiredFields.forEach((field) => {
    if (!field.input.value.trim()) {
      field.input.setAttribute("aria-invalid", "true");
      field.error.textContent = field.message;
      firstInvalid ??= field.input;
    } else {
      clearFieldError(field);
    }
  });
  if (firstInvalid) {
    firstInvalid.focus();
    return;
  }
  shownLevels = [];
  requestHint(1);
});

retryButton.addEventListener("click", () => requestHint(currentLevel || 1));
nextHintButton.addEventListener("click", () => {
  if (currentLevel < 4) requestHint(currentLevel + 1);
});
