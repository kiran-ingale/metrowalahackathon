const form = document.querySelector("#problem-form");
const titleField = document.querySelector("#problem-title");
const statementField = document.querySelector("#problem-statement");
const hintButton = document.querySelector(".hint-button");
const hintButtonLabel = document.querySelector(".hint-label");
const resultCard = document.querySelector("#hint-result");
const hintHeading = document.querySelector("#hint-heading");
const hintLoading = document.querySelector("#hint-loading");
const hintAnswer = document.querySelector("#hint-answer");
const retryButton = document.querySelector("#retry-hint");
let pendingDemo;

const requiredFields = [
  { input: titleField, error: document.querySelector("#title-error"), message: "Add a title so we know which problem you’re working on." },
  { input: statementField, error: document.querySelector("#statement-error"), message: "Paste the problem statement so we can give you a useful nudge." },
];

function clearFieldError(field) {
  field.input.removeAttribute("aria-invalid");
  field.error.textContent = "";
}

function showDemoHint() {
  clearTimeout(pendingDemo);
  resultCard.hidden = false;
  resultCard.setAttribute("aria-busy", "true");
  hintHeading.textContent = `A gentle nudge for ${titleField.value.trim()}`;
  hintLoading.hidden = false;
  hintAnswer.hidden = true;
  retryButton.disabled = true;
  hintButton.disabled = true;
  hintButtonLabel.textContent = "Preparing demo…";

  pendingDemo = setTimeout(() => {
    hintLoading.hidden = true;
    hintAnswer.hidden = false;
    resultCard.setAttribute("aria-busy", "false");
    retryButton.disabled = false;
    hintButton.disabled = false;
    hintButtonLabel.textContent = "Replay demo hint";
  }, 450);
}

requiredFields.forEach((field) => {
  field.input.addEventListener("input", () => {
    clearFieldError(field);
    clearTimeout(pendingDemo);
    resultCard.hidden = true;
    hintButton.disabled = false;
    retryButton.disabled = false;
    hintButtonLabel.textContent = "Get a hint";
  });
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

  showDemoHint();
});

retryButton.addEventListener("click", showDemoHint);
