const chat = document.getElementById("chat");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const statusEl = document.getElementById("status");
const sendBtn = form.querySelector(".btn-send");
const stopBtn = document.getElementById("btn-stop");
const voiceBtn = document.getElementById("voice-btn");
const audioElement = document.getElementById("elevenlabs-audio");

// Goal Tracker elements
const goalTracker = document.getElementById("goal-tracker");
const trackerStatusBadge = document.getElementById("tracker-status-badge");
const trackerGoalName = document.getElementById("tracker-goal-name");

function setBusy(b) {
  busy = b;
  if (sendBtn) sendBtn.style.display = b ? "none" : "";
  if (stopBtn) stopBtn.style.display = b ? "" : "none";
  if (sendBtn) sendBtn.disabled = b;
  setTyping(b);
  if (!b) hidePermissionPopup();
}

if (stopBtn) {
  stopBtn.addEventListener("click", () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "stop" }));
    }
    stopBtn.disabled = true;
    stopBtn.title = "Stopping...";
  });
}

// ── Enhanced Permission Modal ──────────────────────────────────────────
const permOverlay = document.getElementById("permission-overlay");
const permTitle   = document.getElementById("perm-title");
const permCommand = document.getElementById("perm-command");
const permWhat    = document.getElementById("perm-what");
const permWhy     = document.getElementById("perm-why");
const permImpact  = document.getElementById("perm-impact");
const btnAllow    = document.getElementById("btn-allow-kb");
const btnDeny     = document.getElementById("btn-deny-kb");

function showPermissionPopup(data) {
  if (!permOverlay) return;
  if (permTitle) permTitle.textContent = data.what || "Permission Required";
  if (permCommand) permCommand.textContent = data.command || "System Action";
  if (permWhat) permWhat.textContent = data.what || "Performs system change";
  if (permWhy) permWhy.textContent = data.why || "Required to complete goal";
  if (permImpact) permImpact.textContent = data.impact || "Modifies system environment";
  permOverlay.style.display = "flex";
}

function hidePermissionPopup() {
  if (permOverlay) permOverlay.style.display = "none";
}

if (btnAllow) {
  btnAllow.addEventListener("click", () => {
    hidePermissionPopup();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "approve_permission" }));
    }
  });
}
if (btnDeny) {
  btnDeny.addEventListener("click", () => {
    hidePermissionPopup();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "stop" }));
    }
    if (stopBtn) { stopBtn.disabled = false; stopBtn.title = "Stop agent"; }
  });
}

// ── Goal Tracker Phase Update ────────────────────────────────────────────
function updateGoalTracker(phase, goalName) {
  if (!goalTracker) return;
  goalTracker.style.display = "block";
  if (goalName && trackerGoalName) {
    trackerGoalName.textContent = goalName;
  }
  if (trackerStatusBadge) {
    trackerStatusBadge.textContent = phase.toUpperCase();
  }
  const steps = goalTracker.querySelectorAll(".tracker-step");
  let found = false;
  steps.forEach(step => {
    const p = step.dataset.phase;
    if (p === phase) {
      step.className = "tracker-step active";
      found = true;
    } else if (!found) {
      step.className = "tracker-step completed";
    } else {
      step.className = "tracker-step";
    }
  });
}

// ── Web Speech API (Voice Input STT) ─────────────────────────────────────
let recognition = null;
let isRecording = false;

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRec();
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = 'en-US';

  recognition.onstart = () => {
    isRecording = true;
    voiceBtn.classList.add("recording");
    voiceBtn.title = "Listening... (Click to cancel)";
    input.placeholder = "Listening to your voice...";
  };

  recognition.onresult = (event) => {
    let transcript = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    input.value = transcript;
  };

  recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
    isRecording = false;
    voiceBtn.classList.remove("recording");
    input.placeholder = "Tell TREGO your goal (e.g. 'Set up C++ development')...";
  };

  recognition.onend = () => {
    isRecording = false;
    voiceBtn.classList.remove("recording");
    input.placeholder = "Tell TREGO your goal (e.g. 'Set up C++ development')...";
    if (input.value.trim().length > 0) {
      form.dispatchEvent(new Event("submit", { cancelable: true }));
    }
  };

  if (voiceBtn) {
    voiceBtn.addEventListener("click", () => {
      if (isRecording) {
        recognition.stop();
      } else {
        recognition.start();
      }
    });
  }
} else if (voiceBtn) {
  voiceBtn.title = "Voice recognition not supported in this browser.";
  voiceBtn.style.opacity = "0.5";
}

// ── ElevenLabs Voice Output Audio Playback ───────────────────────────────
function playElevenLabsAudio(audioBase64) {
  if (!audioBase64 || !audioElement) return;
  try {
    audioElement.src = `data:audio/mpeg;base64,${audioBase64}`;
    audioElement.play().catch(e => console.log("Audio autoplay note:", e));
  } catch (err) {
    console.warn("Error playing ElevenLabs audio:", err);
  }
}

// ─────────────────────────────────────────────────────────────────────────
const typingIndicator = document.getElementById("typing-indicator");
let ws = null;
let busy = false;

function setTyping(on) {
  typingIndicator.style.display = on ? "flex" : "none";
  if (on) chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
}

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.className = "status " + cls;
}

// ── Conversation Storage ──────────────────────────────────────────
const S_CONVS  = "trego-convs";
const S_ACTIVE = "trego-active-id";
let activeId = null;

function genId() {
  return "c" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
}

function loadConvs() {
  try { return JSON.parse(localStorage.getItem(S_CONVS)) || []; }
  catch { return []; }
}

function saveConvs(convs) {
  try { localStorage.setItem(S_CONVS, JSON.stringify(convs)); } catch {}
}

function getConv(id) {
  return loadConvs().find(c => c.id === id) || null;
}

function createConv() {
  const conv = { id: genId(), title: "New Goal", messages: [] };
  const convs = loadConvs();
  convs.unshift(conv);
  saveConvs(convs);
  return conv;
}

function ensureActive() {
  const saved = localStorage.getItem(S_ACTIVE);
  if (saved && getConv(saved)) {
    activeId = saved;
  } else {
    const convs = loadConvs();
    activeId = convs.length > 0 ? convs[0].id : createConv().id;
    localStorage.setItem(S_ACTIVE, activeId);
  }
}

function setActive(id) {
  activeId = id;
  localStorage.setItem(S_ACTIVE, id);
}

function updateTitle(id, text) {
  const convs = loadConvs();
  const conv = convs.find(c => c.id === id);
  if (conv && (conv.title === "New Goal" || conv.title === "New Chat")) {
    conv.title = text.length > 28 ? text.slice(0, 28) + "…" : text;
    saveConvs(convs);
    renderConvList();
  }
}

function saveMsg(id, msg) {
  const convs = loadConvs();
  const conv = convs.find(c => c.id === id);
  if (!conv) return;
  const stored = { ...msg };
  if (stored.image && stored.image.length > 200000) stored.image = "[image]";
  conv.messages.push(stored);
  saveConvs(convs);
}

function deleteConv(id) {
  const all = loadConvs();
  const deleted = all.find(c => c.id === id);
  if (!deleted) return;
  let convs = all.filter(c => c.id !== id);
  saveConvs(convs);
  if (activeId === id) {
    if (convs.length === 0) convs = [createConv()];
    setActive(convs[0].id);
    renderChat(convs[0].id);
  }
  renderConvList();
}

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ── Intro HTML ────────────────────────────────────────────────────
const INTRO_HTML = `
  <div class="msg intro">
    <div class="intro-content">
      <div class="trego-hero-icon" style="margin-bottom:12px;">
        <svg viewBox="0 0 42 46" width="68" height="68" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="introSkin" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="#ffedd5"/>
              <stop offset="100%" stop-color="#fed7aa"/>
            </linearGradient>
            <linearGradient id="introHair" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#4338ca"/>
              <stop offset="45%" stop-color="#1e1b4b"/>
              <stop offset="100%" stop-color="#0f172a"/>
            </linearGradient>
          </defs>
          <path d="M 9 39 Q 21 35 33 39 L 36 46 L 6 46 Z" fill="#0f172a"/>
          <path d="M 12 40 Q 21 37 30 40" stroke="#00f0ff" stroke-width="1.5" fill="none"/>
          <rect x="18" y="32" width="6" height="7" rx="3" fill="#fdba74"/>
          <ellipse cx="9" cy="24" rx="3.5" ry="4.5" fill="#fed7aa"/>
          <ellipse cx="33" cy="24" rx="3.5" ry="4.5" fill="#fed7aa"/>
          <circle cx="34" cy="24" r="3.2" fill="#0f172a"/>
          <circle cx="34" cy="24" r="1.8" fill="#00f0ff"/>
          <rect x="10" y="12" width="22" height="23" rx="10" fill="url(#introSkin)"/>
          <circle cx="13" cy="27" r="2.5" fill="#f43f5e" opacity="0.3"/>
          <circle cx="29" cy="27" r="2.5" fill="#f43f5e" opacity="0.3"/>
          <path d="M 8 18 Q 8 7 21 6 Q 34 7 34 18 Q 36 12 33 8 Q 28 3 21 3 Q 13 3 9 9 Q 6 13 8 18 Z" fill="url(#introHair)"/>
          <path d="M 8 14 Q 13 18 17 14 Q 21 20 26 13 Q 30 18 34 14 Q 32 10 21 8 Q 11 10 8 14 Z" fill="url(#introHair)"/>
          <rect x="11" y="18" width="8.5" height="8" rx="2.5" fill="rgba(6,182,212,0.15)" stroke="#06b6d4" stroke-width="1"/>
          <rect x="22.5" y="18" width="8.5" height="8" rx="2.5" fill="rgba(6,182,212,0.15)" stroke="#06b6d4" stroke-width="1"/>
          <line x1="19.5" y1="21" x2="22.5" y2="21" stroke="#06b6d4" stroke-width="1"/>
          <ellipse cx="15.2" cy="22.5" rx="3.0" ry="3.8" fill="#0284c7"/>
          <ellipse cx="15.2" cy="22.5" rx="2.0" ry="2.6" fill="#0f172a"/>
          <circle cx="14.3" cy="21.5" r="0.9" fill="#ffffff"/>
          <ellipse cx="26.8" cy="22.5" rx="3.0" ry="3.8" fill="#0284c7"/>
          <ellipse cx="26.8" cy="22.5" rx="2.0" ry="2.6" fill="#0f172a"/>
          <circle cx="25.9" cy="21.5" r="0.9" fill="#ffffff"/>
          <circle cx="21" cy="27" r="0.6" fill="#fb923c"/>
          <path d="M 18 31 Q 21 34 24 31" stroke="#7c2d12" stroke-width="1.3" stroke-linecap="round" fill="none"/>
        </svg>
      </div>
      <h2>Tell it. Let it go.</h2>
      <p>TREGO turns your goal into a verified working result. Click the mic or describe your outcome below.</p>
      <div class="quick-prompts">
        <button class="quick-prompt-chip" onclick="sendQuickGoal('Set up my laptop for C++ development.')">
          ⚡ Set up C++ Development
        </button>
        <button class="quick-prompt-chip" onclick="sendQuickGoal('Prepare my machine for Flutter development and diagnose errors.')">
          🎯 Flutter & Android SDK Setup
        </button>
        <button class="quick-prompt-chip" onclick="sendQuickGoal('Set up Python development environment.')">
          🐍 Python & Virtualenv Setup
        </button>
      </div>
    </div>
  </div>`;

window.sendQuickGoal = function(goalText) {
  input.value = goalText;
  form.dispatchEvent(new Event("submit", { cancelable: true }));
};

function el(cls, text) {
  const d = document.createElement("div");
  d.className = "msg " + cls;
  if (text) d.textContent = text;
  chat.appendChild(d);
  chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
  return d;
}

// ── WebSocket Handler ─────────────────────────────────────────────────
function connect() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${location.host}/ws`);

  ws.onopen = () => {
    setStatus("online", "connected");
  };

  ws.onclose = () => {
    setStatus("offline", "disconnected");
    setTimeout(connect, 2000);
  };

  ws.onerror = (e) => {
    console.error("WS error:", e);
  };

  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      handleAgentEvent(data);
    } catch (err) {
      console.warn("Malformed message:", err);
    }
  };
}

function handleAgentEvent(event) {
  const { kind, payload } = event;

  switch (kind) {
    case "goal_interpreted": {
      updateGoalTracker("understand", `${payload.target_stack.toUpperCase()} Goal`);
      const card = document.createElement("div");
      card.className = "msg trego-card goal-card";
      card.innerHTML = `
        <div class="card-tag">GOAL OBJECTIVE</div>
        <h4>Target: ${esc(payload.target_stack.toUpperCase())} Environment</h4>
        <div class="criteria-list">
          ${(payload.target_state || []).map(s => `<div>• ${esc(s)}</div>`).join("")}
        </div>
      `;
      chat.appendChild(card);
      chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
      break;
    }

    case "inspection_result": {
      updateGoalTracker("inspect");
      const card = document.createElement("div");
      card.className = "msg trego-card inspect-card";
      card.innerHTML = `
        <div class="card-tag">INSPECTION REPORT</div>
        <h4>${esc(payload.module.toUpperCase())} Status: ${payload.is_installed ? '<span style="color:#10b981;">Installed</span>' : '<span style="color:#f59e0b;">Missing</span>'}</h4>
        <div style="font-size:0.88rem;color:#cbd5e1;margin-top:6px;">Version: ${esc(payload.version || 'Not found')}</div>
        ${(payload.issues && payload.issues.length > 0) ? `
          <div style="color:#ef4444;font-size:0.85rem;margin-top:8px;">
            Issues detected: ${payload.issues.map(i => `<div>⚠️ ${esc(i)}</div>`).join("")}
          </div>
        ` : ''}
      `;
      chat.appendChild(card);
      chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
      break;
    }

    case "clarification_required": {
      updateGoalTracker("clarify");
      const card = document.createElement("div");
      card.className = "msg trego-card clarification-card";
      card.innerHTML = `
        <div class="card-tag">CLARIFICATION NEEDED</div>
        <h4>${esc(payload.question)}</h4>
        <div class="clarification-options">
          ${(payload.options || []).map(opt => `
            <button class="btn-clarify-opt" onclick="sendClarificationChoice('${esc(opt)}')">${esc(opt)}</button>
          `).join("")}
        </div>
      `;
      chat.appendChild(card);
      chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
      break;
    }

    case "plan_created": {
      updateGoalTracker("plan");
      const card = document.createElement("div");
      card.className = "msg trego-card plan-card";
      card.innerHTML = `
        <div class="card-tag">EXECUTION PLAN</div>
        <h4>Structured Action Steps</h4>
        <ol style="margin:8px 0 0 16px;padding:0;font-size:0.88rem;color:#e2e8f0;line-height:1.6;">
          ${(payload.steps || []).map(st => `<li><strong>${esc(st.title)}</strong>: ${esc(st.description)}</li>`).join("")}
        </ol>
      `;
      chat.appendChild(card);
      chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
      break;
    }

    case "permission_required": {
      updateGoalTracker("permission");
      showPermissionPopup(payload);
      break;
    }

    case "troubleshoot_step": {
      updateGoalTracker("troubleshoot");
      const card = document.createElement("div");
      card.className = "msg trego-card troubleshoot-card";
      card.innerHTML = `
        <div class="card-tag" style="background:rgba(239,68,68,0.2);color:#ef4444;">DIAGNOSTIC &amp; RECOVERY</div>
        <h4>Cause: ${esc(payload.cause)}</h4>
        <p style="margin:4px 0 0;font-size:0.88rem;color:#cbd5e1;">Proposed fix: ${esc(payload.proposed_action)}</p>
      `;
      chat.appendChild(card);
      chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
      break;
    }

    case "verification_result": {
      updateGoalTracker("verify");
      const card = document.createElement("div");
      card.className = payload.verified ? "msg trego-card verified-success-card" : "msg trego-card verified-fail-card";
      card.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
          <div style="font-size:1.4rem;">${payload.verified ? '✅' : '❌'}</div>
          <h4 style="margin:0;color:#fff;">${payload.verified ? 'Verification Passed &amp; Proven' : 'Verification Failed'}</h4>
        </div>
        <p style="margin:0 0 8px;font-size:0.9rem;color:#cbd5e1;">${esc(payload.evidence || payload.error_message || '')}</p>
        <div style="font-size:0.82rem;color:#94a3b8;">
          ${(payload.checks_passed || []).map(c => `<div>✓ ${esc(c)}</div>`).join("")}
          ${(payload.checks_failed || []).map(c => `<div style="color:#ef4444;">✗ ${esc(c)}</div>`).join("")}
        </div>
      `;
      chat.appendChild(card);
      chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
      break;
    }

    case "voice_audio": {
      if (payload.audio_base64) {
        playElevenLabsAudio(payload.audio_base64);
      }
      break;
    }

    case "status": {
      if (payload.phase) {
        updateGoalTracker(payload.phase);
      }
      el("status", payload.msg || JSON.stringify(payload));
      break;
    }

    case "thought": {
      el("thought", payload.text || JSON.stringify(payload));
      break;
    }

    case "result": {
      setBusy(false);
      break;
    }

    case "error": {
      el("error", "Error: " + (payload.msg || JSON.stringify(payload)));
      setBusy(false);
      break;
    }

    default:
      if (payload && payload.msg) el("status", payload.msg);
  }
}

window.sendClarificationChoice = function(choiceText) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "message", text: choiceText, mode: "control" }));
    el("user", choiceText);
    setBusy(true);
  }
};

// ── Submit Form (Goal Dispatch) ──────────────────────────────────────────
form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text || busy) return;

  el("user", text);
  updateTitle(activeId, text);
  saveMsg(activeId, { kind: "user", text: text });
  input.value = "";
  setBusy(true);

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: "message",
      text: text,
      mode: "control",
    }));
  }
});

// ── Init ─────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  ensureActive();
  renderConvList();
  renderChat(activeId);
  connect();
});

function renderConvList() {
  const convs = loadConvs();
  const list = document.getElementById("conv-list");
  if (!list) return;
  list.innerHTML = convs.map(conv => `
    <div class="conv-item${conv.id === activeId ? " active" : ""}" data-id="${conv.id}">
      <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;opacity:0.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
      <span class="conv-title">${esc(conv.title)}</span>
      <button class="conv-del" data-id="${conv.id}" title="Delete">
        <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>`).join("");
}

function renderChat(id) {
  chat.innerHTML = "";
  setTyping(false);
  const conv = getConv(id);
  if (!conv || conv.messages.length === 0) {
    chat.innerHTML = INTRO_HTML;
    return;
  }
  for (const msg of conv.messages) {
    if (msg.kind === "user") el("user", msg.text);
    else el(msg.kind, msg.text);
  }
  chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" });
}

document.getElementById("btn-new-chat").addEventListener("click", () => {
  const c = createConv();
  setActive(c.id);
  renderConvList();
  renderChat(c.id);
  if (goalTracker) goalTracker.style.display = "none";
});
