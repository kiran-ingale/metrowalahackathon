const BACKEND_URL = "http://127.0.0.1:8000/v1/guidance/hint";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (
    sender.id !== chrome.runtime.id ||
    message?.type !== "UNSTUCK_REQUEST_HINT" ||
    !message.payload
  ) {
    return false;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25_000);

  fetch(BACKEND_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(message.payload),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Backend returned ${response.status}`);
      return response.json();
    })
    .then((payload) => sendResponse({ ok: true, payload }))
    .catch(() => sendResponse({ ok: false }))
    .finally(() => clearTimeout(timeout));

  return true;
});
