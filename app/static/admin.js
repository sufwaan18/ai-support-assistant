const generateButton = document.querySelector("#generate-code");
const masterKey = document.querySelector("#master-key");
const codePanel = document.querySelector("#generated-code");
const codeValue = document.querySelector("#code-value");
const error = document.querySelector("#admin-error");
const countdown = document.querySelector("#code-countdown");
let countdownTimer;

function startCountdown(totalSeconds) {
  window.clearInterval(countdownTimer);
  let remaining = totalSeconds;
  const update = () => {
    const minutes = Math.floor(remaining / 60);
    const seconds = String(remaining % 60).padStart(2, "0");
    countdown.textContent = remaining > 0
      ? `Code and visitor session expire in ${minutes}:${seconds}`
      : "Code and visitor session expired";
    if (remaining <= 0) window.clearInterval(countdownTimer);
    remaining -= 1;
  };
  update();
  countdownTimer = window.setInterval(update, 1000);
}

generateButton.addEventListener("click", async () => {
  error.hidden = true;
  codePanel.hidden = true;
  generateButton.disabled = true;
  generateButton.textContent = "Generating...";

  try {
    const response = await fetch("/access/codes", {
      method: "POST",
      headers: { "X-API-Key": masterKey.value.trim() },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Unable to generate a code.");
    codeValue.textContent = payload.code;
    codePanel.hidden = false;
    startCountdown(payload.expires_in_seconds);
    masterKey.value = "";
  } catch (requestError) {
    error.textContent = requestError.message;
    error.hidden = false;
  } finally {
    generateButton.disabled = false;
    generateButton.textContent = "Generate access code";
  }
});
