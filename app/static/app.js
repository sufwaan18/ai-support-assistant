const form = document.querySelector("#support-form");
const messageInput = document.querySelector("#message");
const submitButton = document.querySelector("#submit-button");
const chatThread = document.querySelector("#chat-thread");
const errorMessage = document.querySelector("#error-message");
const accessGate = document.querySelector("#access-gate");
const accessForm = document.querySelector("#access-form");
const accessCode = document.querySelector("#access-code");
const accessError = document.querySelector("#access-error");
const chatApp = document.querySelector("#chat-app");
const endSessionButton = document.querySelector("#end-session");
const sessionBrand = document.querySelector("#session-brand");
const conversationHistory = [];
let sessionTimer;

function lockChat(message = "Your five-minute access session has expired.") {
  window.clearTimeout(sessionTimer);
  chatApp.hidden = true;
  accessGate.hidden = false;
  chatApp.classList.remove("conversation-started");
  conversationHistory.length = 0;
  chatThread.querySelectorAll(".chat-message").forEach((item) => item.remove());
  accessCode.value = "";
  accessError.textContent = message;
  accessError.hidden = false;
  accessCode.focus();
}

endSessionButton.addEventListener("click", async () => {
  await fetch("/access/logout", { method: "POST" });
  lockChat("Session ended. Enter a new access code to continue.");
});

sessionBrand.addEventListener("click", () => {
  chatApp.classList.remove("conversation-started");
  conversationHistory.length = 0;
  chatThread.querySelectorAll(".chat-message").forEach((item) => item.remove());
  errorMessage.hidden = true;
  messageInput.value = "";
  chatThread.scrollTop = 0;
  messageInput.focus();
});

function scheduleSessionExpiry(seconds) {
  window.clearTimeout(sessionTimer);
  sessionTimer = window.setTimeout(async () => {
    await fetch("/access/logout", { method: "POST" });
    lockChat();
  }, Math.max(0, seconds) * 1000);
}

document.querySelectorAll(".suggestions button").forEach((button) => {
  button.addEventListener("click", () => {
    messageInput.value = button.dataset.message;
    messageInput.focus();
  });
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;

  event.preventDefault();
  if (!submitButton.disabled && messageInput.value.trim()) {
    form.requestSubmit();
  }
});

function deriveSubject(message) {
  const firstThought = message.split(/[.!?]/, 1)[0].trim();
  return (firstThought || "Financial support request").slice(0, 100);
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function buildSources(sources) {
  const sourcesContainer = document.createElement("div");
  sourcesContainer.className = "sources";
  sources.forEach((source) => {
    const card = document.createElement("div");
    card.className = "source-card";

    const title = document.createElement("strong");
    title.textContent = `CFPB complaint ${source.complaint_id}`;

    const details = document.createElement("span");
    details.textContent = `${source.product} · ${source.issue}`;

    card.append(title, details);
    sourcesContainer.append(card);
  });
  return sourcesContainer;
}

function addMessage(role, text, sources = [], note = "") {
  const message = document.createElement("article");
  message.className = `chat-message ${role}`;

  const avatar = document.createElement("span");
  avatar.className = "message-avatar";
  avatar.textContent = role === "assistant" ? "T" : "You";

  const content = document.createElement("div");
  content.className = "message-content";
  const body = document.createElement("div");
  body.className = "answer-text";
  body.textContent = text;
  content.append(body);

  if (sources.length) content.append(buildSources(sources));
  if (note) {
    const disclaimer = document.createElement("p");
    disclaimer.className = "disclaimer";
    disclaimer.textContent = note;
    content.append(disclaimer);
  }

  message.append(avatar, content);
  chatThread.insertBefore(message, errorMessage);
  window.requestAnimationFrame(() => {
    chatThread.scrollTo({ top: chatThread.scrollHeight, behavior: "smooth" });
  });
}

function messageWithHistory(currentMessage) {
  if (!conversationHistory.length) return currentMessage;
  const transcript = conversationHistory
    .slice(-4)
    .map((item) => `${item.role}: ${item.text}`)
    .join("\n");
  return `Continue this support conversation.\n${transcript}\nUser: ${currentMessage}`.slice(-2000);
}

async function checkSession() {
  const response = await fetch("/access/session");
  const payload = await response.json();
  accessGate.hidden = payload.authenticated;
  chatApp.hidden = !payload.authenticated;
  if (payload.authenticated) {
    scheduleSessionExpiry(payload.expires_in_seconds);
    messageInput.focus();
  }
}

accessForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  accessError.hidden = true;
  try {
    const response = await fetch("/access/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: accessCode.value.trim() }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "Access denied.");
    accessGate.hidden = true;
    chatApp.hidden = false;
    scheduleSessionExpiry(payload.expires_in_seconds);
    messageInput.focus();
  } catch (requestError) {
    accessError.textContent = requestError.message;
    accessError.hidden = false;
    accessCode.select();
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorMessage.hidden = true;

  const userMessage = messageInput.value.trim();
  chatApp.classList.add("conversation-started");
  addMessage("user", userMessage);
  messageInput.value = "";

  submitButton.disabled = true;
  submitButton.querySelector("span").textContent = "Thinking...";

  try {
    const response = await fetch("/rag/support", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        subject: deriveSubject(userMessage),
        message: messageWithHistory(userMessage),
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "TyTus could not complete this request.");
    }

    addMessage("assistant", payload.reply, payload.sources, payload.disclaimer);
    conversationHistory.push(
      { role: "User", text: userMessage },
      { role: "TyTus", text: payload.reply },
    );
  } catch (error) {
    showError(error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector("span").textContent = "Ask TyTus";
  }
});

checkSession().catch(() => {
  accessGate.hidden = false;
  chatApp.hidden = true;
});

const canvas = document.querySelector("#neural-network");
const context = canvas.getContext("2d");
const industries = [
  "Finance", "Sports", "IT", "Crypto", "Healthcare", "Retail",
  "Energy", "Media", "Education", "Travel", "Insurance", "Real Estate",
  "Banking", "E-commerce", "Telecom", "Automotive", "Logistics", "AI",
];
let nodes = [];
let animationFrame;

function resizeNetwork() {
  const density = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = window.innerWidth * density;
  canvas.height = window.innerHeight * density;
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  context.setTransform(density, 0, 0, density, 0, 0);

  nodes = industries.map((label, index) => ({
    label,
    x: ((index * 149) % Math.max(window.innerWidth - 100, 200)) + 50,
    y: ((index * 97) % Math.max(window.innerHeight - 100, 300)) + 50,
    vx: (index % 2 ? 1 : -1) * (0.08 + (index % 4) * 0.025),
    vy: (index % 3 ? 1 : -1) * (0.07 + (index % 5) * 0.018),
    radius: index % 4 === 0 ? 3.4 : 2.5,
  }));
}

function drawNetwork() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  context.clearRect(0, 0, width, height);

  nodes.forEach((node) => {
    node.x += node.vx;
    node.y += node.vy;
    if (node.x < 30 || node.x > width - 30) node.vx *= -1;
    if (node.y < 35 || node.y > height - 30) node.vy *= -1;
  });

  for (let first = 0; first < nodes.length; first += 1) {
    for (let second = first + 1; second < nodes.length; second += 1) {
      const dx = nodes[first].x - nodes[second].x;
      const dy = nodes[first].y - nodes[second].y;
      const distance = Math.hypot(dx, dy);
      if (distance < 230) {
        context.beginPath();
        context.moveTo(nodes[first].x, nodes[first].y);
        context.lineTo(nodes[second].x, nodes[second].y);
        context.strokeStyle = `rgba(105, 57, 181, ${0.15 * (1 - distance / 230)})`;
        context.lineWidth = 0.8;
        context.stroke();
      }
    }
  }

  nodes.forEach((node) => {
    context.beginPath();
    context.arc(node.x, node.y, node.radius + 5, 0, Math.PI * 2);
    context.fillStyle = "rgba(127, 75, 207, 0.055)";
    context.fill();
    context.beginPath();
    context.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
    context.fillStyle = "rgba(94, 42, 174, 0.46)";
    context.fill();
    context.font = "600 9px DM Sans";
    context.textAlign = "center";
    context.fillStyle = "rgba(70, 44, 105, 0.54)";
    context.fillText(node.label, node.x, node.y - 11);
  });

  animationFrame = window.requestAnimationFrame(drawNetwork);
}

resizeNetwork();
if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  drawNetwork();
} else {
  drawNetwork();
  window.cancelAnimationFrame(animationFrame);
}
window.addEventListener("resize", resizeNetwork);
