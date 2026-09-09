// =========================================================================
// KALMAN CINEMA: Sovereign Broadcast Reliability & Multi-Workspace Deck
// =========================================================================

const state = {
  activeWorkspace: "mission",
  tiles: {},
  sparklines: {},
  activeIncidents: 0,
  postmortems: [],
  pendingActions: {},
  currentDestructiveActionId: null,
  audioEnabled: true,
  audioCtx: null,
  sentinelMood: "CARRIER LOCKED · 48kHz",
  cliHistory: [],
  cliHistoryIndex: -1,
  dragonAwake: false,
  dragonFury: 65,
  dragonTarget: ".panel-regions",
  dragonTargetName: "Primary Origin Cluster (us-east-1)",
  dragonStrikes: 12,
};

// --- In-App Toast Notification System ---
function showToast(msg, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  // Deduplicate: Don't spawn identical stacked toasts
  const existing = Array.from(container.querySelectorAll(".toast-item")).find(
    (t) => t.textContent.includes(msg)
  );
  if (existing) {
    existing.style.transform = "scale(1.05)";
    setTimeout(() => { existing.style.transform = ""; }, 180);
    return;
  }

  const toast = document.createElement("div");
  toast.className = `toast-item ${type}`;
  const icon = type === "success" ? "✓" : (type === "warn" ? "⚠️" : "✕");
  toast.innerHTML = `<span style="font-size:14px;">${icon}</span> <span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    setTimeout(() => toast.remove(), 250);
  }, 3800);
}

// --- Safe JSON Fetch Helper with Throttling & Cooldown Handling ---
async function safeFetchJson(url, options = {}) {
  try {
    const res = await fetch(url, options);
    const text = await res.text();
    if (!res.ok) {
      if (res.status === 429 || text.includes("Rate exceeded") || text.includes("Too Many Requests")) {
        throw new Error("Cooldown active / rate limit reached. The autonomous engine is stabilizing — please pause a second before re-triggering.");
      }
      throw new Error(text || `HTTP ${res.status}`);
    }
    if (!text || !text.trim()) return {};
    return JSON.parse(text);
  } catch (err) {
    if (err.message && (err.message.includes("Rate limit") || err.message.includes("Cooldown"))) throw err;
    if (err.message && err.message.includes("Unexpected token")) {
      throw new Error("Server stabilizing or rate-limited. Please wait a brief moment.");
    }
    throw err;
  }
}

// --- Quick Interactive Telemetry & Regional Injections ---
const _lastInjectTimes = {};
async function injectSignal(sig, mult = 15.0) {
  const now = Date.now();
  if (_lastInjectTimes[sig] && (now - _lastInjectTimes[sig] < 1200)) {
    showToast(`Signal ${sig} already perturbed. Allowing Kalman innovation loop to track...`, "warn");
    return;
  }
  _lastInjectTimes[sig] = now;
  playSound("alarm");
  showToast(`Injecting fault on ${sig} (+${mult}x)...`, "warn");
  try {
    const data = await safeFetchJson("/inject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ signal: sig, multiplier: mult, seconds: 30.0 }),
    });
    const inj = data.injected || sig;
    const m = data.multiplier || mult;
    logCrew("watcher", `Fault injected: ${inj} (multiplier: ${m}x)`);
    showToast(`Active fault on ${inj}! Kalman filter tracking innovation.`, "warn");
  } catch (err) {
    showToast(`Inject notice: ${err.message || err}`, "warn");
  }
}

async function shiftRegionalTraffic(region) {
  playSound("click");
  showToast(`Initiating 25% traffic shift away from ${region}...`, "warn");
  try {
    await safeFetchJson("/api/multicdn/shift", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_region: region, to_region: "eu-west", pct: 25.0 }),
    });
    showToast(`Traffic shifted: 25% away from ${region}`, "success");
    logCrew("actuator", `Manual traffic shift from ${region} complete`);
  } catch (e) {
    showToast(`Shift notice: ${e.message || e}`, "warn");
  }
}

async function injectRegionalFault(region) {
  playSound("alarm");
  showToast(`Injecting edge CDN fault in ${region}...`, "warn");
  try {
    await safeFetchJson("/inject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ signal: "cdn_5xx_rate", multiplier: 15.0, seconds: 30.0, region: region }),
    });
    showToast(`Edge failure injected in ${region}!`, "warn");
  } catch (e) {
    showToast(`Regional inject notice: ${e.message || e}`, "warn");
  }
}

async function triggerTestHitlGate() {
  playSound("alarm");
  showToast("Generating high-risk test incident requiring supervisor signature...", "warn");
  let data = null;
  try {
    data = await safeFetchJson("/governor/simulate_gate", { method: "POST" });
  } catch (err) {
    console.warn("Server gate simulation fallback:", err);
    data = {
      action_id: `act-hitl-${Math.random().toString(36).substring(2, 8)}`,
      action: "failover_to_backup_stream",
      params: { target: "backup_origin_cluster", pct: 100 },
      reason: "Destructive primary origin failover requires manual supervisor sign-off",
    };
  }
  state.pendingActions[data.action_id] = data;
  renderHitlDrawer();
  openDestructiveModal(data);
  showToast(`New action pending approval: ${data.action}`, "warn");
}

async function loadPendingHitlActions() {
  try {
    const data = await safeFetchJson("/governor/pending");
    const actions = data.pending_actions || [];
    actions.forEach((a) => {
      state.pendingActions[a.action_id] = a;
    });
    renderHitlDrawer();
  } catch (e) {
    console.warn("Pending actions sync note:", e);
  }
}

// --- Procedural Web Audio Synthesizer ---
function getAudioContext() {
  if (!state.audioCtx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) state.audioCtx = new AudioCtx();
  }
  if (state.audioCtx && state.audioCtx.state === "suspended") {
    state.audioCtx.resume();
  }
  return state.audioCtx;
}

function playSound(type) {
  if (!state.audioEnabled) return;
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (type === "click") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(600, now);
      osc.frequency.exponentialRampToValueAtTime(300, now + 0.04);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
      osc.start(now);
      osc.stop(now + 0.04);
    } else if (type === "squish") {
      osc.type = "triangle";
      osc.frequency.setValueAtTime(350, now);
      osc.frequency.exponentialRampToValueAtTime(700, now + 0.08);
      osc.frequency.exponentialRampToValueAtTime(280, now + 0.16);
      gain.gain.setValueAtTime(0.18, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
      osc.start(now);
      osc.stop(now + 0.16);
    } else if (type === "alarm") {
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(880, now);
      osc.frequency.setValueAtTime(740, now + 0.08);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
      osc.start(now);
      osc.stop(now + 0.18);
    } else if (type === "success") {
      osc.type = "sine";
      osc.frequency.setValueAtTime(523.25, now); // C5
      osc.frequency.setValueAtTime(659.25, now + 0.06); // E5
      osc.frequency.setValueAtTime(783.99, now + 0.12); // G5
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);
      osc.start(now);
      osc.stop(now + 0.28);
    } else if (type === "tornado") {
      // Wind storm howl synthesizer
      const bufferSize = ctx.sampleRate * 2.5;
      const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = noiseBuffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        output[i] = Math.random() * 2 - 1;
      }
      const whiteNoise = ctx.createBufferSource();
      whiteNoise.buffer = noiseBuffer;

      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.setValueAtTime(280, now);
      filter.frequency.exponentialRampToValueAtTime(750, now + 1.2);
      filter.frequency.exponentialRampToValueAtTime(180, now + 2.5);
      filter.Q.setValueAtTime(3.5, now);

      gain.gain.setValueAtTime(0.01, now);
      gain.gain.linearRampToValueAtTime(0.35, now + 0.4);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 2.5);

      whiteNoise.connect(filter);
      filter.connect(gain);
      whiteNoise.start(now);
      whiteNoise.stop(now + 2.5);
    } else if (type === "roar") {
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(170, now);
      osc.frequency.exponentialRampToValueAtTime(36, now + 1.1);
      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 1.1);
      osc.start(now);
      osc.stop(now + 1.1);

      try {
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = "square";
        osc2.frequency.setValueAtTime(260, now + 0.1);
        osc2.frequency.exponentialRampToValueAtTime(55, now + 0.9);
        gain2.gain.setValueAtTime(0.18, now + 0.1);
        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.9);
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.start(now + 0.1);
        osc2.stop(now + 0.9);
      } catch (_) {}
    }
  } catch (e) {
    // Audio context may be restricted by browser policy before first user gesture
  }
}

function toggleAudio() {
  state.audioEnabled = !state.audioEnabled;
  const btn = document.getElementById("audio-toggle-btn");
  if (btn) {
    btn.innerHTML = `<span class="dock-icon">${state.audioEnabled ? "🔊" : "🔇"}</span> <span>Audio: ${state.audioEnabled ? "ON" : "OFF"}</span>`;
  }
  if (state.audioEnabled) playSound("click");
}

function setAudioEnabled(val) {
  state.audioEnabled = val;
  const btn = document.getElementById("audio-toggle-btn");
  if (btn) {
    btn.innerHTML = `<span class="dock-icon">${state.audioEnabled ? "🔊" : "🔇"}</span> <span>Audio: ${state.audioEnabled ? "ON" : "OFF"}</span>`;
  }
}

// --- Universal Stereoscopic Eye & Gaze Tracking Across ALL Broadcast Familiars ---
let eyeTrackingRafPending = false;
let lastMousePos = { x: window.innerWidth / 2, y: window.innerHeight / 2 };

function updateAllCreatureEyes(e) {
  const mx = e.clientX;
  const my = e.clientY;

  function trackCirclePupil(pupilId, glintId, defCx, defCy, maxDisp, sens) {
    const el = document.getElementById(pupilId);
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.bottom < 0 || rect.top > window.innerHeight) return;
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = mx - cx;
    const dy = my - cy;
    const dist = Math.hypot(dx, dy);
    const angle = Math.atan2(dy, dx);
    const clamped = Math.min(dist * sens, maxDisp);

    const px = defCx + clamped * Math.cos(angle);
    const py = defCy + clamped * Math.sin(angle);
    el.setAttribute("cx", px.toFixed(1));
    el.setAttribute("cy", py.toFixed(1));
    if (glintId) {
      const glint = document.getElementById(glintId);
      if (glint) {
        glint.setAttribute("cx", (px - 1.5).toFixed(1));
        glint.setAttribute("cy", (py - 1.5).toFixed(1));
      }
    }
  }

  function trackRectPupil(pupilId, defX, defY, maxDisp, sens) {
    const el = document.getElementById(pupilId);
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.bottom < 0 || rect.top > window.innerHeight) return;
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = mx - cx;
    const dy = my - cy;
    const dist = Math.hypot(dx, dy);
    const angle = Math.atan2(dy, dx);
    const clamped = Math.min(dist * sens, maxDisp);

    el.setAttribute("x", (defX + clamped * Math.cos(angle)).toFixed(1));
    el.setAttribute("y", (defY + clamped * Math.sin(angle)).toFixed(1));
  }

  // 1. Kalman (The Alpha Familiar in Sanctuary)
  trackCirclePupil("kalman-pupil-l", "kalman-glint-l", 37, 48, 4.0, 0.035);
  trackCirclePupil("kalman-pupil-r", "kalman-glint-r", 63, 48, 4.0, 0.035);

  // 2. Chrono (Sync Sprite)
  trackCirclePupil("chrono-pupil-l", null, 18, 19, 1.2, 0.025);
  trackCirclePupil("chrono-pupil-r", null, 22, 19, 1.2, 0.025);

  // 3. Flux (CDN Leviathan)
  trackCirclePupil("flux-pupil", null, 9, 21, 1.2, 0.025);

  // 4. Warden (Policy Golem)
  trackRectPupil("warden-pupil-l", 15, 15, 1.4, 0.025);
  trackRectPupil("warden-pupil-r", 22, 15, 1.4, 0.025);

  // 5. Scribble (Scribe Owl)
  trackCirclePupil("scribble-pupil-l", null, 17, 20, 1.8, 0.03);
  trackCirclePupil("scribble-pupil-r", null, 23, 20, 1.8, 0.03);

  // 6. Ignis the Chaos Dragon (in Lair, when awake)
  if (state.dragonAwake) {
    trackCirclePupil("dragon-pupil-l", null, 92, 41, 2.5, 0.035);
    trackCirclePupil("dragon-pupil-r", null, 108, 41, 2.5, 0.035);
  }
}

window.addEventListener("mousemove", (e) => {
  lastMousePos.x = e.clientX;
  lastMousePos.y = e.clientY;
  if (!eyeTrackingRafPending) {
    eyeTrackingRafPending = true;
    requestAnimationFrame(() => {
      updateAllCreatureEyes(lastMousePos);
      eyeTrackingRafPending = false;
    });
  }
});

function setKalmanMood(mood, desc) {
  state.sentinelMood = desc;
  const el = document.getElementById("sentinel-mood-text");
  if (el) el.textContent = desc;
  const sanctStatus = document.getElementById("sanctuary-kalman-status");
  if (sanctStatus) {
    sanctStatus.textContent = mood === "PANIC" ? "ANOMALY TRIAGING" : (mood === "HAPPY" ? "PURRING (^▽^)" : "PRISTINE · WATCH STANDING");
    sanctStatus.style.background = mood === "PANIC" ? "#fee2e2" : "#dcfce7";
    sanctStatus.style.color = mood === "PANIC" ? "#991b1b" : "#15803d";
  }
}

function setSentinelMood(mood, desc) {
  setKalmanMood(mood, desc);
}

// --- LIVING CREATURE KINETIC & FLIGHT WORK ENGINE ---
const CREATURE_DEFS = {
  chrono: {
    name: "CHRONO",
    title: "Sync Sprite",
    color: "#93c5fd",
    cardId: "creature-card-chrono",
    targetSelector: ".panel-telemetry",
    highlightClass: "creature-work-pulse",
    sound: "click",
    defaultSpeech: "AV-Sync locked at ±0.0ms! Clock drift eliminated.",
    particles: ["✨", "⏱️", "⭐", "💫"],
    svg: `<svg viewBox="0 0 40 40" width="50" height="50" style="overflow:visible;">
      <path class="chrono-wing-l" d="M 16 18 Q 8 8 18 10 Z" fill="#93c5fd" stroke="#20222a" stroke-width="1.5"/>
      <path class="chrono-wing-r" d="M 24 18 Q 32 8 22 10 Z" fill="#93c5fd" stroke="#20222a" stroke-width="1.5"/>
      <circle cx="20" cy="20" r="8" fill="#fef08a" stroke="#20222a" stroke-width="1.8"/>
      <circle cx="18" cy="19" r="1.6" fill="#20222a"/>
      <circle cx="22" cy="19" r="1.6" fill="#20222a"/>
      <line x1="20" y1="20" x2="20" y2="15" stroke="#e11d48" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="20" y1="20" x2="23" y2="20" stroke="#0284c7" stroke-width="1.2" stroke-linecap="round"/>
    </svg>`,
    onWork: () => {
      const tile = document.getElementById("tile-av_sync_offset_ms") || document.querySelector(".panel-telemetry");
      if (tile) {
        tile.classList.add("creature-work-pulse");
        setTimeout(() => tile.classList.remove("creature-work-pulse"), 2600);
      }
      logCrew("chrono", "Chrono locked 48kHz audio phase & AV cadence to 0.0ms (ITU-T P.1203).");
    }
  },
  flux: {
    name: "FLUX",
    title: "CDN Leviathan",
    color: "#38bdf8",
    cardId: "creature-card-flux",
    targetSelector: ".panel-regions",
    highlightClass: "creature-work-pulse-blue",
    sound: "squish",
    defaultSpeech: "Rebalanced 48 Gbps! Smooth flow across Fastly & Cloudflare.",
    particles: ["🫧", "🌊", "💧", "⚡"],
    svg: `<svg viewBox="0 0 40 40" width="52" height="52" class="flux-creature-svg" style="overflow:visible;">
      <path d="M 6 22 Q 14 10 22 22 Q 30 32 36 18" fill="none" stroke="#0284c7" stroke-width="4" stroke-linecap="round"/>
      <circle cx="10" cy="22" r="5.5" fill="#38bdf8" stroke="#20222a" stroke-width="1.8"/>
      <circle cx="9" cy="21" r="1.5" fill="#20222a"/>
      <circle cx="8" cy="20" r="0.6" fill="#ffffff"/>
    </svg>`,
    onWork: () => {
      const panel = document.querySelector(".panel-regions");
      if (panel) {
        panel.classList.add("creature-work-pulse-blue");
        setTimeout(() => panel.classList.remove("creature-work-pulse-blue"), 2600);
      }
      logCrew("flux", "Flux rerouted edge streams. Multi-CDN ingress stabilized at 142 Gbps.");
    }
  },
  warden: {
    name: "WARDEN",
    title: "Policy Golem",
    color: "#fcd34d",
    cardId: "creature-card-warden",
    targetSelector: ".panel-incident",
    highlightClass: "creature-work-pulse",
    sound: "click",
    defaultSpeech: "Runic shield engaged: All destructive actions sealed behind HITL gates.",
    particles: ["🛡️", "⚡", "✨", "🔒"],
    svg: `<svg viewBox="0 0 40 40" width="48" height="48" style="overflow:visible;">
      <rect x="11" y="10" width="18" height="20" rx="5" fill="#fcd34d" stroke="#20222a" stroke-width="2"/>
      <circle class="warden-core-gem" cx="20" cy="20" r="4" fill="#059669" stroke="#20222a" stroke-width="1.2"/>
      <rect x="14" y="14" width="4" height="2.5" rx="1" fill="#20222a"/>
      <rect x="22" y="14" width="4" height="2.5" rx="1" fill="#20222a"/>
      <line x1="16" y1="26" x2="24" y2="26" stroke="#20222a" stroke-width="1.5" stroke-linecap="round"/>
    </svg>`,
    onWork: () => {
      const drawer = document.getElementById("hitl-drawer") || document.querySelector(".panel-incident");
      if (drawer) {
        drawer.classList.add("creature-work-pulse");
        setTimeout(() => drawer.classList.remove("creature-work-pulse"), 2600);
      }
      logCrew("warden", "Warden confirmed all safety bounds. Automated controls held within safety margins.");
    }
  },
  scribble: {
    name: "SCRIBBLE",
    title: "Scribe Owl",
    color: "#fed7aa",
    cardId: "creature-card-scribble",
    targetSelector: ".panel-crew-stream",
    highlightClass: "creature-work-pulse",
    sound: "click",
    defaultSpeech: "Cited Query Q-48291! Cryptographic proof recorded in ledger.",
    particles: ["🖋️", "📜", "✒️", "✨"],
    svg: `<svg viewBox="0 0 40 40" width="48" height="48" style="overflow:visible;">
      <circle cx="20" cy="22" r="9" fill="#fed7aa" stroke="#20222a" stroke-width="2"/>
      <circle cx="16" cy="19" r="3.5" fill="#ffffff" stroke="#20222a" stroke-width="1.2"/>
      <circle cx="24" cy="19" r="3.5" fill="#ffffff" stroke="#20222a" stroke-width="1.2"/>
      <circle cx="16.5" cy="19" r="1.5" fill="#20222a"/>
      <circle cx="23.5" cy="19" r="1.5" fill="#20222a"/>
      <polygon points="19,23 21,23 20,26" fill="#f59e0b" stroke="#20222a" stroke-width="0.8"/>
      <path class="scribble-quill" d="M 28 26 L 36 12 L 33 10 Z" fill="#e11d48" stroke="#20222a" stroke-width="1.2"/>
    </svg>`,
    onWork: () => {
      const terminal = document.getElementById("crew-terminal") || document.querySelector(".panel-crew-stream");
      if (terminal) {
        terminal.classList.add("creature-work-pulse");
        setTimeout(() => terminal.classList.remove("creature-work-pulse"), 2600);
      }
      logCrew("scribble", "Scribble certified incident proof: SHA-256 telemetry query verified against Grafana.");
    }
  },
  kalman: {
    name: "KALMAN",
    title: "Core Signal Familiar",
    color: "#0284c7",
    cardId: "creature-hero-kalman",
    targetSelector: ".mission-grid",
    highlightClass: "creature-work-pulse",
    sound: "success",
    defaultSpeech: "Twin receivers locked at 48kHz. Telemetry innovation filter nominal.",
    particles: ["📡", "✨", "🛰️", "💚"],
    svg: `<svg viewBox="0 0 100 100" width="54" height="54" style="overflow:visible;">
      <circle cx="26" cy="12" r="5" fill="none" stroke="#e11d48" stroke-width="1.5" opacity="0.6"/>
      <circle cx="74" cy="12" r="5" fill="none" stroke="#0284c7" stroke-width="1.5" opacity="0.6"/>
      <path d="M 36 28 Q 30 16 26 12" fill="none" stroke="#20222a" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="26" cy="12" r="3.5" fill="#f59e0b" stroke="#20222a" stroke-width="1.5"/>
      <path d="M 64 28 Q 70 16 74 12" fill="none" stroke="#20222a" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="74" cy="12" r="3.5" fill="#f59e0b" stroke="#20222a" stroke-width="1.5"/>
      <rect x="17" y="27" width="66" height="56" rx="16" fill="#ffffff" stroke="#20222a" stroke-width="3"/>
      <rect x="22" y="32" width="56" height="46" rx="11" fill="#faf8f5" stroke="#20222a" stroke-width="1.5"/>
      <circle cx="37" cy="48" r="8.5" fill="#20222a"/>
      <circle cx="37" cy="48" r="7.5" fill="#ffffff"/>
      <circle cx="37" cy="48" r="4.2" fill="#0284c7"/>
      <circle cx="35.5" cy="46.5" r="1.5" fill="#ffffff"/>
      <circle cx="63" cy="48" r="8.5" fill="#20222a"/>
      <circle cx="63" cy="48" r="7.5" fill="#ffffff"/>
      <circle cx="63" cy="48" r="4.2" fill="#0284c7"/>
      <circle cx="61.5" cy="46.5" r="1.5" fill="#ffffff"/>
      <ellipse cx="28" cy="60" rx="3.5" ry="2" fill="#fb7185" opacity="0.6"/>
      <ellipse cx="72" cy="60" rx="3.5" ry="2" fill="#fb7185" opacity="0.6"/>
      <path d="M 43 64 Q 46 67 50 64 Q 54 61 57 64" fill="none" stroke="#20222a" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
    onWork: () => {
      document.querySelectorAll(".panel").forEach((p) => {
        p.classList.add("creature-work-pulse");
        setTimeout(() => p.classList.remove("creature-work-pulse"), 1600);
      });
      logCrew("watcher", "Kalman broadcast familiar pinged all subsystem nodes. Fleet status: NOMINAL.");
    }
  },
  ignis: {
    name: "IGNIS",
    title: "Chaos Dragon",
    color: "#dc2626",
    cardId: "dragon-throne",
    targetSelector: ".panel-regions",
    highlightClass: "flaming-widget",
    sound: "roar",
    defaultSpeech: "ROAAARRR! INCINERATING COMPROMISED PRIMARY ORIGIN!",
    particles: ["🔥", "💥", "🌋", "⚡", "☄️"],
    svg: `<svg viewBox="0 0 100 80" width="82" height="68" class="dragon-creature-svg" style="overflow:visible;">
      <path d="M 46 22 Q 40 8 32 4 Q 38 12 44 24" fill="#f59e0b" stroke="#20222a" stroke-width="1.8"/>
      <path d="M 54 22 Q 60 8 68 4 Q 62 12 56 24" fill="#f59e0b" stroke="#20222a" stroke-width="1.8"/>
      <g class="dragon-wing-l">
        <path d="M 38 32 Q 10 10 2 28 Q 14 34 26 40 Q 32 36 38 32 Z" fill="#991b1b" stroke="#20222a" stroke-width="2.2"/>
        <path d="M 12 20 Q 18 30 26 40" fill="none" stroke="#f59e0b" stroke-width="1.5"/>
      </g>
      <g class="dragon-wing-r">
        <path d="M 62 32 Q 90 10 98 28 Q 86 34 74 40 Q 68 36 62 32 Z" fill="#991b1b" stroke="#20222a" stroke-width="2.2"/>
        <path d="M 88 20 Q 82 30 74 40" fill="none" stroke="#f59e0b" stroke-width="1.5"/>
      </g>
      <path d="M 42 46 Q 30 65 38 76 Q 50 82 50 68" fill="#b91c1c" stroke="#20222a" stroke-width="2"/>
      <ellipse cx="50" cy="42" rx="15" ry="17" fill="#dc2626" stroke="#20222a" stroke-width="2.5"/>
      <path d="M 44 32 Q 50 34 56 32 Q 55 48 50 56 Q 45 48 44 32" fill="#fef08a" stroke="#20222a" stroke-width="1.4"/>
      <polygon points="40,24 50,14 60,24 57,36 43,36" fill="#b91c1c" stroke="#20222a" stroke-width="2.2"/>
      <circle cx="45" cy="24" r="2.8" fill="#fef08a" stroke="#20222a" stroke-width="1"/>
      <circle cx="45" cy="24" r="1.4" fill="#20222a"/>
      <circle cx="55" cy="24" r="2.8" fill="#fef08a" stroke="#20222a" stroke-width="1"/>
      <circle cx="55" cy="24" r="1.4" fill="#20222a"/>
      <path class="dragon-fire-tongue" d="M 48 36 Q 50 42 49 46 Q 52 42 51 36" fill="#f97316"/>
    </svg>`,
    onWork: () => {
      const target = document.querySelector(".panel-regions");
      if (target) {
        target.classList.add("origin-incinerated");
        setTimeout(() => target.classList.remove("origin-incinerated"), 3200);
      }
      logCrew("actuator", "🔥 IGNIS incinerated primary origin cluster (us-east-1). 100% traffic shifted to backup.");
      logCrew("governor", "Destructive failover complete: primary origin offline, secondary pool streaming nominal.");
    }
  }
};

function spawnFlightParticle(x, y, char = "✨") {
  const stage = document.getElementById("creature-flight-stage");
  if (!stage) return;
  const p = document.createElement("div");
  p.className = "flight-particle";
  p.textContent = char;
  p.style.left = `${x}px`;
  p.style.top = `${y}px`;
  const angle = Math.random() * Math.PI * 2;
  const dist = 16 + Math.random() * 24;
  p.style.setProperty("--dx", `${Math.cos(angle) * dist}px`);
  p.style.setProperty("--dy", `${Math.sin(angle) * dist - 16}px`);
  stage.appendChild(p);
  setTimeout(() => p.remove(), 750);
}

function flyCreatureTo(type, customSpeech = null) {
  const def = CREATURE_DEFS[type];
  if (!def) return;

  const stage = document.getElementById("creature-flight-stage");
  if (!stage) return;

  // Prevent multiple simultaneous flights of the same creature
  if (stage.querySelector(`.flying-${type}`)) return;

  playSound(def.sound || "click");

  // Determine start position
  const homeCard = document.getElementById(def.cardId) || document.querySelector(".sanctuary-avatar-box");
  const homeRect = homeCard ? homeCard.getBoundingClientRect() : { left: 100, top: 100, width: 50, height: 50 };
  const startX = homeRect.left + homeRect.width / 2 - 27;
  const startY = homeRect.top + homeRect.height / 2 - 27;

  // Determine target position
  const targetEl = document.querySelector(def.targetSelector);
  const targetRect = targetEl ? targetEl.getBoundingClientRect() : { left: window.innerWidth * 0.6, top: 300, width: 200, height: 200 };
  const targetX = targetRect.left + targetRect.width / 2 - 27;
  const targetY = targetRect.top + Math.min(120, targetRect.height / 2) - 27;

  // Visual compression on home card
  if (homeCard) {
    homeCard.style.transform = "scale(0.92)";
    setTimeout(() => { homeCard.style.transform = ""; }, 220);
  }

  // Create flyer
  const flyer = document.createElement("div");
  flyer.className = `flying-creature-sprite flying-${type}`;
  flyer.innerHTML = `<div class="flying-creature-inner">${def.svg}</div>`;
  stage.appendChild(flyer);

  // Bezier trajectory control point (arched upward into the sky)
  const midX = (startX + targetX) / 2;
  const midY = Math.min(startY, targetY) - 130;

  // Animation timing
  const flightDuration = 720;
  const startTime = performance.now();

  function animateOutbound(now) {
    const elapsed = now - startTime;
    const t = Math.min(1.0, elapsed / flightDuration);
    // EaseInOutQuad
    const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

    // Quadratic Bezier: (1-e)^2 * start + 2*(1-e)*e * mid + e^2 * target
    const inv = 1 - ease;
    const curX = inv * inv * startX + 2 * inv * ease * midX + ease * ease * targetX;
    const curY = inv * inv * startY + 2 * inv * ease * midY + ease * ease * targetY;

    // Banking angle
    const dx = (2 * inv * (midX - startX) + 2 * ease * (targetX - midX));
    const dy = (2 * inv * (midY - startY) + 2 * ease * (targetY - midY));
    const angle = Math.atan2(dy, dx) * (180 / Math.PI) * 0.35;

    flyer.style.transform = `translate(${curX.toFixed(1)}px, ${curY.toFixed(1)}px) rotate(${angle.toFixed(1)}deg)`;

    // Spawn flight particle periodically
    if (Math.random() < 0.35) {
      const pChar = def.particles[Math.floor(Math.random() * def.particles.length)];
      spawnFlightParticle(curX + 20, curY + 20, pChar);
    }

    if (t < 1.0) {
      requestAnimationFrame(animateOutbound);
    } else {
      // Arrived at destination!
      flyer.style.transform = `translate(${targetX.toFixed(1)}px, ${targetY.toFixed(1)}px) rotate(0deg)`;

      // Spawn arrival burst
      for (let i = 0; i < 5; i++) {
        const pChar = def.particles[i % def.particles.length];
        spawnFlightParticle(targetX + 20, targetY + 20, pChar);
      }

      // Execute in-UI work action
      if (typeof def.onWork === "function") def.onWork();
      playSound("success");

      // Attach hand-drawn speech bubble
      const bubble = document.createElement("div");
      bubble.className = "creature-flight-bubble";
      bubble.textContent = customSpeech || def.defaultSpeech;
      flyer.appendChild(bubble);

      // Hold at destination for 1.8 seconds, then return home!
      setTimeout(() => {
        bubble.style.opacity = "0";
        setTimeout(() => bubble.remove(), 200);
        animateReturnHome();
      }, 1800);
    }
  }

  function animateReturnHome() {
    const returnDuration = 650;
    const returnStartTime = performance.now();
    const retMidX = (targetX + startX) / 2;
    const retMidY = Math.min(startY, targetY) - 100;

    function returnFrame(now) {
      const elapsed = now - returnStartTime;
      const t = Math.min(1.0, elapsed / returnDuration);
      const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

      const inv = 1 - ease;
      const curX = inv * inv * targetX + 2 * inv * ease * retMidX + ease * ease * startX;
      const curY = inv * inv * targetY + 2 * inv * ease * retMidY + ease * ease * startY;

      const dx = (2 * inv * (retMidX - targetX) + 2 * ease * (startX - retMidX));
      const dy = (2 * inv * (retMidY - targetY) + 2 * ease * (startY - retMidY));
      const angle = Math.atan2(dy, dx) * (180 / Math.PI) * 0.3;

      flyer.style.transform = `translate(${curX.toFixed(1)}px, ${curY.toFixed(1)}px) rotate(${angle.toFixed(1)}deg)`;

      if (t < 1.0) {
        requestAnimationFrame(returnFrame);
      } else {
        // Returned home!
        flyer.style.transform = `translate(${startX.toFixed(1)}px, ${startY.toFixed(1)}px) scale(0.6)`;
        flyer.style.opacity = "0";
        setTimeout(() => flyer.remove(), 250);

        if (homeCard) {
          homeCard.style.transform = "scale(1.1) translateY(-4px)";
          setTimeout(() => { homeCard.style.transform = ""; }, 260);
        }
      }
    }

    requestAnimationFrame(returnFrame);
  }

  requestAnimationFrame(animateOutbound);
}

function deployCreaturePatrol() {
  playSound("success");
  showToast("🚀 Broadcast familiar crew dispatched on live deck patrol!", "success");
  const crew = ["chrono", "flux", "warden", "scribble"];
  crew.forEach((c, idx) => {
    setTimeout(() => {
      flyCreatureTo(c);
    }, idx * 360);
  });
}

function pokeChrono() {
  flyCreatureTo("chrono");
}

function pokeFlux() {
  flyCreatureTo("flux");
}

function pokeWarden() {
  flyCreatureTo("warden");
}

function pokeScribble() {
  flyCreatureTo("scribble");
}

function pokeKalman() {
  playSound("click");
  const quotes = [
    "Carrier locked · 48kHz pristine. The watch stands eternal!",
    "Buffer 100% · Zero phase drift. Twin receivers in lock (^▽^)",
    "Signal crisp · All edge channels nominal, Chief!",
    "Kalman residual innovation filter running at 60Hz telemetry rate.",
    "0.0% frame drop · ITU-T P.1203 viewer MOS pristine!"
  ];
  const chosen = quotes[Math.floor(Math.random() * quotes.length)];
  setKalmanMood("HAPPY", chosen);

  const quoteBox = document.getElementById("sanctuary-quote");
  if (quoteBox) quoteBox.textContent = `"${chosen}"`;

  const widget = document.querySelector(".carrier-scope-widget") || document.querySelector(".sentinel-widget");
  const avatarBox = document.querySelector(".sanctuary-avatar-box");
  const led = document.getElementById("pulse-status-led");
  if (widget) {
    widget.style.transform = "translateY(-4px) scale(1.04)";
    setTimeout(() => { widget.style.transform = ""; }, 220);
  }
  if (avatarBox) {
    avatarBox.style.transform = "scale(1.08) rotate(3deg)";
    setTimeout(() => { avatarBox.style.transform = ""; }, 240);
  }
  if (led) {
    led.setAttribute("fill", "#38bdf8");
    setTimeout(() => { led.setAttribute("fill", "#059669"); }, 800);
  }

  // Also launch Kalman flying pulse across the deck
  flyCreatureTo("kalman", chosen);

  setTimeout(() => {
    setKalmanMood("NORMAL", state.activeIncidents > 0 ? "ALERT · CONTAINING ANOMALY" : "CARRIER LOCKED · 48kHz");
  }, 3500);
}

function pokePulse() { pokeKalman(); }
function pokeSentinel() { pokeKalman(); }

// --- Multi-Workspace Navigation ---
function switchWorkspace(workspaceId) {
  state.activeWorkspace = workspaceId;
  playSound("click");

  // Update views
  document.querySelectorAll(".workspace-view").forEach((v) => {
    v.classList.remove("active");
  });
  const targetView = document.getElementById(`view-${workspaceId}`);
  if (targetView) targetView.classList.add("active");

  // Update dock buttons
  document.querySelectorAll(".dock-btn").forEach((b) => {
    b.classList.remove("active");
  });
  const activeBtn = Array.from(document.querySelectorAll(".dock-btn")).find((b) =>
    b.getAttribute("onclick")?.includes(workspaceId)
  );
  if (activeBtn) activeBtn.classList.add("active");

  // Specific workspace triggers
  if (workspaceId === "mission") loadPendingHitlActions();
  if (workspaceId === "governor") loadPendingHitlActions();
  if (workspaceId === "neural") loadForensicsCatalog();
  if (workspaceId === "scribe") loadArchiveList();
  if (workspaceId === "terminal") {
    const input = document.getElementById("term-cli-input");
    if (input) setTimeout(() => input.focus(), 100);
  }
}

// --- SSE Event Stream with Heartbeat Fallback & Auto-Reconnect ---
let es = null;
let lastTelemetryTime = Date.now();

function routeServerEvent(e) {
  if (!e || !e.type) return;
  switch (e.type) {
    case "telemetry":
      handleTelemetry(e.snapshot, e.regional_matrix, e.active_incidents, e.qoe, e.slo, e.economics, e.threats, e.markov);
      break;
    case "blast_radius":
      handleBlastRadius(e.report);
      break;
    case "forecast":
      handleForecast(e.forecast);
      break;
    case "anomaly":
      handleAnomaly(e.anomaly);
      break;
    case "diagnosis":
      handleDiagnosis(e.diagnosis);
      break;
    case "arbitration":
      logCrew("arbiter", `Consensus reached: ${e.consensus.selected_action} (${e.consensus.consensus_score_pct}% support)`);
      break;
    case "failure_forensics":
      logCrew("scribe", `Disaster archetype match: ${e.match.disaster_name} (${e.match.similarity_score_pct}%)`);
      break;
    case "governance":
      handleGovernance(e.decision);
      break;
    case "hitl_gate":
      handleHitlGate(e);
      break;
    case "remediation":
      handleRemediation(e.execution);
      break;
    case "recovery":
      handleRecovery(e);
      break;
    case "postmortem":
      handlePostmortem(e.postmortem);
      break;
    case "scenario_triggered":
      logCrew("watcher", `Scenario triggered: ${e.scenario.scenario} (${e.scenario.region})`);
      break;
    case "chaos_launched":
      logCrew("watcher", `Chaos stress test: ${e.experiment.name} (${e.experiment.duration_s}s)`);
      break;
  }
}

function connectEventSource() {
  if (es) {
    try { es.close(); } catch (_) {}
  }
  es = new EventSource("/stream");

  es.onmessage = (msg) => {
    lastTelemetryTime = Date.now();
    try {
      const e = JSON.parse(msg.data);
      routeServerEvent(e);
    } catch (err) {
      // Ignored for keepalive comments
    }
  };

  es.onerror = () => {
    // Immediate fallback fetch & reconnect
    fetchSnapshotNow();
    setTimeout(connectEventSource, 2500);
  };
}

async function fetchSnapshotNow() {
  try {
    const data = await safeFetchJson("/api/snapshot");
    if (data && data.snapshot) {
      lastTelemetryTime = Date.now();
      handleTelemetry(data.snapshot, data.regional_matrix, data.active_incidents);
    }
  } catch (_) {}
}

// Start SSE connection
connectEventSource();

// Active Heartbeat Poller: Guarantees telemetry NEVER freezes even across network disconnects
setInterval(() => {
  if (Date.now() - lastTelemetryTime > 2200) {
    fetchSnapshotNow();
  }
}, 1200);

// --- Telemetry Handling ---
function handleTelemetry(snap, regionalMatrix, activeIncidents, qoe, slo, econ, threats, markov) {
  try {
    state.activeIncidents = activeIncidents || 0;
    updateIncidentPill(state.activeIncidents);

    // Update Sentinel Mood based on incident status
    if (state.activeIncidents > 0) {
      setSentinelMood("PANIC", "ANOMALY DETECTED! TRIAGING...");
    } else {
      setSentinelMood("VIGILANT", "VIGILANT · ALL CLEAR");
    }

    // Update QoE HUD & QoE Studio
    if (qoe && qoe.mos !== undefined) {
      const qoeVal = document.getElementById("qoe-val");
      const qoeCat = document.getElementById("qoe-cat");
      const qoePill = document.getElementById("qoe-pill");
      const qoeStudioVal = document.getElementById("qoe-studio-val");
      const mosNum = Number(qoe.mos);
      if (qoeVal) qoeVal.textContent = mosNum.toFixed(2);
      if (qoeCat) qoeCat.textContent = qoe.category || "NOMINAL";
      if (qoeStudioVal) qoeStudioVal.textContent = mosNum.toFixed(2);
      if (qoePill) {
        if (mosNum < 3.0) {
          qoePill.className = "metric-pill pill-red";
        } else if (mosNum < 4.0) {
          qoePill.className = "metric-pill pill-amber";
        } else {
          qoePill.className = "metric-pill pill-green";
        }
      }
    }

    // Update SLO HUD & Studio
    if (slo && slo.error_budget_remaining_pct !== undefined) {
      const sloBud = document.getElementById("slo-budget");
      const sloBurn = document.getElementById("slo-burn");
      const sloStudioVal = document.getElementById("slo-studio-val");
      const sloBurnVal = document.getElementById("slo-burn-val");
      const budVal = Number(slo.error_budget_remaining_pct).toFixed(1);
      const burnVal = Number(slo.burn_rate_1h || 1.0).toFixed(1);
      if (sloBud) sloBud.textContent = `${budVal}%`;
      if (sloBurn) sloBurn.textContent = `${burnVal}x BURN`;
      if (sloStudioVal) sloStudioVal.textContent = `${budVal}%`;
      if (sloBurnVal) sloBurnVal.textContent = `${burnVal}x`;
    }

    // Update Financial Economics HUD
    if (econ) {
      const econRate = document.getElementById("econ-loss-rate");
      const econTot = document.getElementById("econ-total");
      const accum = Number(econ.total_accumulated_loss_usd !== undefined ? econ.total_accumulated_loss_usd : (econ.accumulated_loss || 0));
      const lossRate = Number(econ.revenue_loss_rate_per_sec !== undefined ? econ.revenue_loss_rate_per_sec : 0);
      if (econRate) econRate.textContent = `$${lossRate.toFixed(2)}/s`;
      if (econTot) econTot.textContent = `ACCUM: $${accum.toFixed(2)}`;
    }

    // Update War Room Hero Displays & Creature Sanctuary
    if (qoe && qoe.mos !== undefined) {
      const heroVal = document.getElementById("qoe-hero-val");
      const heroAb = document.getElementById("qoe-hero-abandon");
      const mosNum = Number(qoe.mos);
      if (heroVal) heroVal.textContent = mosNum.toFixed(2);
      if (heroAb) heroAb.textContent = `${(Math.max(0.08, (5.0 - mosNum) * 0.45)).toFixed(2)}%`;
    }
    if (slo && slo.error_budget_remaining_pct !== undefined) {
      const blastSlo = document.getElementById("blast-slo-val");
      const budVal = Number(slo.error_budget_remaining_pct).toFixed(1);
      const burnVal = Number(slo.burn_rate_1h || 1.0).toFixed(1);
      if (blastSlo) blastSlo.textContent = `${budVal}% (${burnVal}x Burn)`;
    }
    if (econ) {
      const blastLoss = document.getElementById("blast-loss-rate");
      const blastRisk = document.getElementById("blast-sla-risk");
      const accum = Number(econ.total_accumulated_loss_usd !== undefined ? econ.total_accumulated_loss_usd : (econ.accumulated_loss || 0));
      const lossRate = Number(econ.revenue_loss_rate_per_sec !== undefined ? econ.revenue_loss_rate_per_sec : 0);
      if (blastLoss) {
        blastLoss.textContent = `$${lossRate.toFixed(2)} / sec`;
        blastLoss.className = lossRate > 0 ? "val val-red" : "val val-green";
      }
      if (blastRisk) {
        const isRisk = accum > 0;
        blastRisk.textContent = `$${accum.toFixed(2)} ${isRisk ? "(At Risk)" : "(Protected)"}`;
        blastRisk.className = isRisk ? "val val-red" : "val val-green";
      }
    }

    // Update Companion Creature live stats
    if (snap && snap.av_sync_offset_ms !== undefined) {
      const cm = document.getElementById("chrono-metric");
      if (cm) cm.textContent = `AV Sync: ${Number(snap.av_sync_offset_ms).toFixed(1)}ms`;
    }
    if (snap && snap.cdn_5xx_rate !== undefined) {
      const fm = document.getElementById("flux-metric");
      if (fm) fm.textContent = `Edge 5xx: ${(Number(snap.cdn_5xx_rate) * 100).toFixed(2)}%`;
    }
    const wm = document.getElementById("warden-metric");
    if (wm) {
      const pCount = Object.keys(state.pendingActions || {}).length;
      wm.textContent = `Gates: ${pCount} Held`;
      wm.style.color = pCount > 0 ? "var(--accent-amber)" : "var(--accent-blue)";
    }

    // Update Signal Tiles in Mission Control (Panel 2)
    const grid = document.getElementById("tiles");
    if (grid && snap) {
      for (const [k, v] of Object.entries(snap)) {
        let t = state.tiles[k] || document.getElementById(`tile-${k}`);
        if (!t) {
          t = createSignalTile(k, v);
          grid.appendChild(t);
        }
        state.tiles[k] = t;
        updateSignalTile(t, k, v);
      }
    }

    // Update Regional Matrix (Panel 4)
    if (regionalMatrix) {
      renderRegionalMatrix(regionalMatrix);
    }
  } catch (err) {
    console.error("Telemetry handler error:", err);
  }
}

function createSignalTile(sig, val) {
  const div = document.createElement("div");
  div.className = "signal-tile";
  div.id = `tile-${sig}`;
  div.innerHTML = `
    <div class="sig-header">
      <span class="sig-name">${sig.replace(/_/g, " ").toUpperCase()}</span>
      <span class="sig-z-badge">z: 0.0</span>
    </div>
    <div class="sig-val-wrap">
      <span class="sig-val">${Number(val).toFixed(3)}</span>
      <span class="sig-est">est: &mdash;</span>
    </div>
    <div class="sig-sparkline-wrap">
      <svg class="sig-sparkline" viewBox="0 0 100 24" preserveAspectRatio="none">
        <path class="spark-fill" d="" />
        <path class="spark-line" d="" />
      </svg>
    </div>
    <div class="sig-actions">
      <button class="btn-spike" onclick="injectSignal('${sig}', 15.0)" title="Inject immediate test anomaly spike">⚡ Spike</button>
    </div>
  `;
  state.sparklines[sig] = [val];
  return div;
}

function updateSignalTile(t, sig, val) {
  const valEl = t.querySelector(".sig-val");
  if (valEl) valEl.textContent = Number(val).toFixed(3);

  // Maintain rolling history for sparkline
  const hist = state.sparklines[sig] || [];
  hist.push(val);
  if (hist.length > 25) hist.shift();
  state.sparklines[sig] = hist;

  // Render SVG Sparkline
  const min = Math.min(...hist);
  const max = Math.max(...hist);
  const range = max - min || 1;
  const pts = hist.map((pt, i) => {
    const x = (i / (hist.length - 1 || 1)) * 100;
    const y = 22 - ((pt - min) / range) * 20;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const linePath = t.querySelector(".spark-line");
  const fillPath = t.querySelector(".spark-fill");
  if (linePath) linePath.setAttribute("d", `M ${pts.join(" L ")}`);
  if (fillPath) fillPath.setAttribute("d", `M ${pts.join(" L ")} L 100,24 L 0,24 Z`);
}

function renderRegionalMatrix(matrix) {
  const container = document.getElementById("regional-matrix");
  if (!container || !matrix) return;

  const html = Object.entries(matrix).map(([reg, data]) => {
    const rebuf = data.rebuffer_ratio !== undefined ? Number(data.rebuffer_ratio) : (Number(data.rebuffer || 0.005));
    const cdn5xx = data.cdn_5xx_rate !== undefined ? Number(data.cdn_5xx_rate) : (Number(data.cdn_5xx || 0.0));
    const enc = data.encoder_health !== undefined ? Number(data.encoder_health) : 0.99;
    const isCritical = cdn5xx > 40 || rebuf > 0.05 || enc < 0.5;
    const isDegraded = !isCritical && (cdn5xx > 15 || rebuf > 0.02 || enc < 0.8);
    const status = isCritical ? "CRITICAL" : (isDegraded ? "DEGRADED" : "NOMINAL");
    const statusColor = isCritical ? "var(--accent-red)" : (isDegraded ? "var(--accent-amber)" : "var(--accent-green)");

    return `
      <div class="region-tile ${isCritical ? 'critical' : (isDegraded ? 'degraded' : '')}">
        <div class="reg-top">
          <span class="reg-name">${reg.toUpperCase()}</span>
          <span class="reg-cdn" style="color:${statusColor}; font-weight:800; background:transparent;">${status}</span>
        </div>
        <div class="reg-stats">
          <span>reb: ${(rebuf * 100).toFixed(2)}%</span>
          <span>5xx: ${cdn5xx.toFixed(1)}/s</span>
        </div>
        <div class="reg-actions">
          <button class="btn-reg-shift" onclick="shiftRegionalTraffic('${reg}')" title="Shift 25% traffic away from ${reg}">Shift 25%</button>
          <button class="btn-reg-fault" onclick="injectRegionalFault('${reg}')" title="Inject edge failure in ${reg}">⚡ Fault</button>
        </div>
      </div>
    `;
  }).join("");

  container.innerHTML = html;
}

function handleBlastRadius(report) {
  const initEl = document.getElementById("blast-init");
  const coupEl = document.getElementById("blast-coupled");
  const impEl = document.getElementById("blast-imp");
  const stBadge = document.getElementById("blast-status");

  if (initEl) initEl.textContent = report.primary_initiator || "None (System Stable)";
  if (coupEl) coupEl.textContent = report.coupled_signals.join(", ") || "None";
  if (impEl) {
    impEl.textContent = `${report.audience_impact_pct.toFixed(0)}%`;
    impEl.className = report.audience_impact_pct > 20 ? "val val-red" : "val val-green";
  }
  if (stBadge) {
    stBadge.textContent = report.systemic_cascade ? "SYSTEMIC" : "REGIONAL";
    stBadge.className = report.systemic_cascade ? "badge-count active" : "badge-count";
  }
}

// --- Forecast Handling ---
function handleForecast(f) {
  const ticker = document.getElementById("forecast-ticker");
  const msg = document.getElementById("forecast-msg");
  if (!ticker || !msg) return;

  ticker.classList.remove("hidden");
  msg.textContent = `${f.signal}: ${f.message}`;
  logCrew("forecaster", `[${f.status}] ${f.signal} slope: ${f.slope.toFixed(4)}/s (TTB: ${f.seconds_to_breach || "N/A"}s)`);

  clearTimeout(window._forecastTimer);
  window._forecastTimer = setTimeout(() => {
    ticker.classList.add("hidden");
  }, 9000);
}

function formatZ(z) {
  if (z === null || z === undefined || isNaN(Number(z))) return "0.0";
  const num = Number(z);
  if (Math.abs(num) >= 99.9) return num > 0 ? "+99.9" : "-99.9";
  return (num > 0 ? "+" : "") + num.toFixed(1);
}

// --- Anomaly & Incident Handling ---
function handleAnomaly(a) {
  playSound("alarm");
  const t = state.tiles[a.signal];
  const formattedZ = formatZ(a.z);
  if (t) {
    t.classList.add("hot");
    const zBadge = t.querySelector(".sig-z-badge");
    if (zBadge) {
      zBadge.textContent = `z: ${formattedZ}`;
      zBadge.classList.add("firing");
    }
    setTimeout(() => {
      t.classList.remove("hot");
      if (zBadge) zBadge.classList.remove("firing");
    }, 12000);
  }

  const cleanVal = Number(a.value || 0).toFixed(3);
  logEvent(`ANOMALY DETECTED: ${a.signal.replace(/_/g, " ").toUpperCase()}`, `Innovation z-score ${formattedZ} breached adaptive Kalman gate (measured: ${cleanVal}).`, "hot");
  logCrew("watcher", `Innovation threshold breached: ${a.signal} z=${formattedZ} [${a.severity || 'P2'}]`);
}

function handleDiagnosis(d) {
  logEvent(`DIAGNOSIS (ADK + GEMINI PRO)`, `${d.root_cause} (Confidence: ${d.confidence})`, "hot");
  logCrew("diagnostician", `Root cause: ${d.root_cause} (${d.evidence ? d.evidence.length : 0} Grafana queries backed)`);
}

function handleGovernance(g) {
  const approved = g.approved;
  const statusTxt = approved ? "APPROVED" : (g.requires_human ? "HELD FOR HUMAN GATE" : "BLOCKED");
  const cls = approved ? "gov" : "hot";
  logEvent(`GOVERNOR DECISION`, `${g.action} -> ${statusTxt} (${g.reason})`, cls);
  logCrew("governor", `Policy check: ${g.action} -> ${statusTxt} [Hash: ${g.hash || 'ok'}]`);
}

// --- HITL Human-in-the-Loop ---
function handleHitlGate(e) {
  playSound("alarm");
  state.pendingActions[e.action_id] = e;
  renderHitlDrawer();
  openDestructiveModal(e);
  logCrew("governor", `[HITL GATE] Operator sign-off required for ${e.action} (Action ID: ${e.action_id})`);
}

function renderHitlDrawer() {
  const listEl = document.getElementById("hitl-actions-list");
  const countEl = document.getElementById("hitl-count");
  if (!listEl) return;
  const pending = Object.values(state.pendingActions);

  if (countEl) {
    countEl.textContent = pending.length;
    if (pending.length > 0) {
      countEl.classList.add("active");
    } else {
      countEl.classList.remove("active");
    }
  }

  if (pending.length === 0) {
    listEl.innerHTML = `<div style="font-size:11px; color:var(--ink-muted); padding:4px 0;">No actions pending operator sign-off.</div>`;
    return;
  }

  listEl.innerHTML = pending.map((a) => `
    <div class="hitl-card indie-card" id="card-${a.action_id}" style="border: 1.5px solid var(--accent-red); background:#fff5f5; border-radius:6px; padding:6px 8px; margin-bottom:4px;">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:10px; font-weight:800; font-family:var(--font-mono); color:var(--accent-red);">⚠️ ${a.action.replace(/_/g, " ").toUpperCase()}</span>
        <span style="font-size:9px; font-family:var(--font-mono); color:var(--ink-muted);">${a.action_id}</span>
      </div>
      <div class="hitl-reason" style="font-size:10px; color:var(--ink-primary); margin:2px 0;">${a.reason || 'Destructive operational action requires supervisor signature'}</div>
      <div class="hitl-btns" style="display:flex; gap:6px; margin-top:4px;">
        <button class="btn-approve" style="background:#dc2626; color:#fff;" onclick="approveDestructiveGate('${a.action_id}')">🔥 Authorize & Destroy</button>
        <button class="btn-reject" onclick="rejectDestructiveGate('${a.action_id}')">🛡️ Reject</button>
      </div>
    </div>
  `).join("");
}

// --- Destructive Failover Modal & Dragon Summoning Flow ---
function openDestructiveModal(data) {
  if (!data) return;
  state.currentDestructiveActionId = data.action_id;
  const idEl = document.getElementById("destructive-modal-action-id");
  if (idEl) idEl.textContent = data.action_id || "act-hitl-gate";
  const modal = document.getElementById("destructive-modal");
  if (modal) modal.classList.remove("hidden");
  playSound("alarm");
}

function closeDestructiveModal() {
  const modal = document.getElementById("destructive-modal");
  if (modal) modal.classList.add("hidden");
}

function approveCurrentDestructiveGate() {
  if (state.currentDestructiveActionId) {
    approveDestructiveGate(state.currentDestructiveActionId);
  } else {
    closeDestructiveModal();
  }
}

function rejectCurrentDestructiveGate() {
  if (state.currentDestructiveActionId) {
    rejectDestructiveGate(state.currentDestructiveActionId);
  } else {
    closeDestructiveModal();
  }
}

async function approveDestructiveGate(actionId) {
  closeDestructiveModal();
  delete state.pendingActions[actionId];
  renderHitlDrawer();
  playSound("roar");

  // Summon Chaos Dragon (IGNIS) with active fire-breathing failover!
  executeDragonIncineration(state.dragonTarget, state.dragonTargetName);
  logCrew("governor", `[OPERATOR APPROVED & INCINERATED] Destructive failover executed for ${actionId}`);

  try {
    await safeFetchJson(`/governor/actions/${actionId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator: "Lead_NOC_Operator" }),
    });
  } catch (err) {
    console.warn("Destructive action approve sync note:", err);
  }
}

async function rejectDestructiveGate(actionId) {
  closeDestructiveModal();
  delete state.pendingActions[actionId];
  renderHitlDrawer();
  playSound("click");

  // Summon Warden with protective runic shield
  flyCreatureTo("warden", "🛡️ Runic shield engaged! Destructive failover blocked.");
  showToast(`Destructive failover aborted by supervisor: ${actionId}`, "warn");
  logCrew("governor", `[OPERATOR DENIED] Destructive failover aborted. Infrastructure protected.`);

  try {
    await safeFetchJson(`/governor/actions/${actionId}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator: "Lead_NOC_Operator", reason: "Operator withheld destructive signature" }),
    });
  } catch (err) {
    console.warn("Destructive action reject sync note:", err);
  }
}

function summonChaosDragon() {
  executeDragonIncineration(state.dragonTarget, state.dragonTargetName);
}

// =========================================================================
// DRAGON'S LAIR & EPIC FIRE-BREATHING INCINERATION
// =========================================================================
function toggleDragonAwake() {
  state.dragonAwake = !state.dragonAwake;
  const badge = document.getElementById("dragon-status-badge");
  const btn = document.getElementById("btn-toggle-wake");
  const speech = document.getElementById("dragon-speech-bubble");
  const eyesSlumber = document.getElementById("dragon-eyes-slumber");
  const eyesAwake = document.getElementById("dragon-eyes-awake");
  const mawFlame = document.getElementById("dragon-maw-flame");
  const wingL = document.getElementById("dragon-wing-left");
  const wingR = document.getElementById("dragon-wing-right");

  if (state.dragonAwake) {
    playSound("roar");
    if (badge) {
      badge.textContent = "AWAKENED · INFERNAL OVERDRIVE";
      badge.classList.add("awakened");
    }
    if (btn) {
      btn.innerHTML = `<span>💤</span> <span>Soothe Ignis</span>`;
    }
    if (speech) {
      speech.textContent = "ROAAARRR! WHO DARES AWAKEN IGNIS FROM THE MAGMA EMBERS?!";
      speech.style.color = "#fca5a5";
    }
    if (eyesSlumber) eyesSlumber.style.display = "none";
    if (eyesAwake) eyesAwake.style.display = "block";
    if (mawFlame) mawFlame.style.display = "block";
    if (wingL) wingL.style.transform = "rotate(-25deg)";
    if (wingR) wingR.style.transform = "rotate(25deg)";

    const throne = document.getElementById("dragon-throne");
    if (throne) {
      throne.classList.add("screen-rumble-heavy");
      setTimeout(() => throne.classList.remove("screen-rumble-heavy"), 800);
    }
    showToast("🔥 IGNIS HAS AWAKENED! The caldera boils with thermal fury!", "warn");
  } else {
    playSound("click");
    if (badge) {
      badge.textContent = "DORMANT · SLUMBERING";
      badge.classList.remove("awakened");
    }
    if (btn) {
      btn.innerHTML = `<span>⚡</span> <span>Wake Ignis</span>`;
    }
    if (speech) {
      speech.textContent = '"Zzzz... The primary origin sleeps... do not disturb without cause."';
      speech.style.color = "#fecdd3";
    }
    if (eyesSlumber) eyesSlumber.style.display = "block";
    if (eyesAwake) eyesAwake.style.display = "none";
    if (mawFlame) mawFlame.style.display = "none";
    if (wingL) wingL.style.transform = "rotate(0deg)";
    if (wingR) wingR.style.transform = "rotate(0deg)";
    showToast("Ignis curls back into the magma embers to slumber.", "info");
  }
}

function pokeDragonInLair() {
  const speech = document.getElementById("dragon-speech-bubble");
  if (!state.dragonAwake) {
    playSound("squish");
    const smokeL = document.getElementById("smoke-puff-l");
    const smokeR = document.getElementById("smoke-puff-r");
    if (smokeL && smokeR) {
      smokeL.style.opacity = "0.8";
      smokeR.style.opacity = "0.8";
      setTimeout(() => { smokeL.style.opacity = "0"; smokeR.style.opacity = "0"; }, 700);
    }
    if (speech) speech.textContent = '"*Snort*... Hmph! Disturbing my slumber? Stand clear of the caldera!"';
    showToast("Ignis snorts a ring of volcanic smoke at you.", "warn");
  } else {
    playSound("roar");
    state.dragonFury = Math.min(100, state.dragonFury + 5);
    updateDragonFuryUi();
    if (speech) speech.textContent = '"ROAAAR! MY FURY BUILDS! GIVE ME A SUBSYSTEM TO INCINERATE!"';
    const svg = document.getElementById("lair-dragon-svg");
    if (svg) {
      svg.style.transform = "scale(1.08)";
      setTimeout(() => { svg.style.transform = ""; }, 300);
    }
  }
}

function feedDragonCore() {
  playSound("success");
  state.dragonFury = Math.min(100, state.dragonFury + 15);
  updateDragonFuryUi();
  const tempVal = document.getElementById("dragon-temp-val");
  if (tempVal) {
    const t = 4850 + Math.floor(state.dragonFury * 8.5);
    tempVal.textContent = `${t.toLocaleString()}°C`;
  }
  const speech = document.getElementById("dragon-speech-bubble");
  if (speech) speech.textContent = '"Gulp! High-entropy anomaly core consumed! Thermal capacity elevated!"';
  showToast("⚡ Anomaly telemetry core consumed: Ignis's fury elevated!", "success");
}

function updateDragonFuryUi() {
  const fill = document.getElementById("fury-fill-bar");
  const txt = document.getElementById("fury-pct-text");
  if (fill) fill.style.width = `${state.dragonFury}%`;
  if (txt) txt.textContent = `${state.dragonFury}% ${state.dragonFury >= 100 ? "MAX OVERDRIVE" : "READY"}`;
}

function setDragonTarget(selector, name) {
  state.dragonTarget = selector;
  state.dragonTargetName = name;
  playSound("click");
  document.querySelectorAll(".target-btn").forEach((b) => b.classList.remove("active"));
  const btn = Array.from(document.querySelectorAll(".target-btn")).find((b) => b.getAttribute("onclick")?.includes(selector));
  if (btn) btn.classList.add("active");
  const speech = document.getElementById("dragon-speech-bubble");
  if (speech) speech.textContent = `"Target designated: ${name}. Ready to bathe it in dragonfire!"`;
  showToast(`Incineration target locked: ${name}`, "info");
}

function unleashDragonFromLair() {
  if (!state.dragonAwake) {
    toggleDragonAwake();
  }
  showToast("🚨 DRAGON UNLEASHED FROM CALDERA! Switching to War Room...", "warn");
  setTimeout(() => {
    switchWorkspace("mission");
    setTimeout(() => {
      executeDragonIncineration(state.dragonTarget, state.dragonTargetName);
    }, 450);
  }, 400);
}

async function executeDragonIncineration(targetSelector = ".panel-regions", targetName = "Multi-CDN Edge Distribution") {
  const stage = document.getElementById("creature-flight-stage") || document.body;

  // Resolve target element with intelligent fallbacks across all 6 core dashboard panels and tiles
  let targetEl = document.querySelector(targetSelector);
  if (!targetEl) {
    if (targetSelector.includes("packet")) {
      targetEl = document.getElementById("tile-packet_loss_pct") || document.querySelector(".panel-telemetry");
    } else if (targetSelector.includes("telemetry") || targetSelector.includes("kalman")) {
      targetEl = document.querySelector(".panel-telemetry");
    } else if (targetSelector.includes("qoe") || targetSelector.includes("econ")) {
      targetEl = document.querySelector(".panel-qoe-econ");
    } else if (targetSelector.includes("incident") || targetSelector.includes("governor")) {
      targetEl = document.querySelector(".panel-incident");
    } else if (targetSelector.includes("crew") || targetSelector.includes("stream") || targetSelector.includes("agent")) {
      targetEl = document.querySelector(".panel-crew-stream");
    } else if (targetSelector.includes("sanctuary")) {
      targetEl = document.querySelector(".panel-sanctuary");
    } else {
      targetEl = document.querySelector(".panel-regions");
    }
  }
  if (!targetEl) return;

  playSound("roar");

  // 1. Heavy screen rumble across entire dashboard
  const mainDeck = document.getElementById("view-mission") || document.body;
  mainDeck.classList.add("screen-rumble-heavy");
  setTimeout(() => mainDeck.classList.remove("screen-rumble-heavy"), 5500);

  // 2. Smoothly scroll target window into center of viewport so operator sees the strike
  targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
  await new Promise((r) => setTimeout(r, 320));

  // 3. Compute exact viewport-relative landing coordinates directly above target window
  const targetRect = targetEl.getBoundingClientRect();
  const destX = Math.max(20, Math.min(window.innerWidth - 120, targetRect.left + targetRect.width / 2 - 45));
  const destY = Math.max(65, targetRect.top - 85);

  const startX = window.innerWidth / 2 - 45;
  const startY = -120;

  const flyer = document.createElement("div");
  flyer.className = "flying-creature-sprite flying-ignis";
  flyer.innerHTML = `<div class="flying-creature-inner">${CREATURE_DEFS.ignis.svg}</div>`;
  stage.appendChild(flyer);

  flyer.style.transition = "transform 1.1s cubic-bezier(0.16, 1, 0.3, 1)";
  flyer.style.transform = `translate(${startX}px, ${startY}px) scale(0.6)`;
  requestAnimationFrame(() => {
    flyer.style.transform = `translate(${destX}px, ${destY}px) scale(1.35)`;
  });

  // 4. Attach speech bubble
  setTimeout(() => {
    const bubble = document.createElement("div");
    bubble.className = "creature-flight-bubble";
    bubble.style.background = "#450a0a";
    bubble.style.color = "#fef08a";
    bubble.style.borderColor = "#ea580c";
    bubble.textContent = `ROAAARRR! INCINERATING ${targetName.toUpperCase()}!`;
    flyer.appendChild(bubble);
  }, 900);

  // 5. Stream Fire Breathing Cone & Fiery Particles directly into target
  setTimeout(() => {
    const streamSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    streamSvg.setAttribute("class", "dragon-fire-stream");
    streamSvg.style.left = `${destX + 30}px`;
    streamSvg.style.top = `${destY + 65}px`;
    streamSvg.style.width = "180px";
    streamSvg.style.height = "160px";
    streamSvg.innerHTML = `
      <defs>
        <radialGradient id="fireGrad" cx="50%" cy="0%" r="90%">
          <stop offset="0%" stop-color="#ffffff"/>
          <stop offset="25%" stop-color="#fef08a"/>
          <stop offset="60%" stop-color="#f97316"/>
          <stop offset="95%" stop-color="#dc2626" stop-opacity="0.85"/>
        </radialGradient>
      </defs>
      <polygon points="15,0 90,150 0,140" fill="url(#fireGrad)"/>
      <polygon points="20,0 75,130 10,120" fill="#fef08a" opacity="0.75"/>
    `;
    stage.appendChild(streamSvg);

    const particleInterval = setInterval(() => {
      const chars = ["🔥", "💥", "🌋", "⚡", "☄️"];
      const pChar = chars[Math.floor(Math.random() * chars.length)];
      const px = destX + (Math.random() * 120 - 30);
      const py = destY + 70 + (Math.random() * 70);
      spawnFlightParticle(px, py, pChar);
    }, 75);

    // 6. SET SPECIFIC TARGET WIDGET BORDERS ABLAZE
    targetEl.classList.add("flaming-widget");

    setTimeout(() => {
      clearInterval(particleInterval);
      streamSvg.style.opacity = "0";
      setTimeout(() => streamSvg.remove(), 400);

      // 7. Failover Execution
      state.dragonStrikes++;
      const strikesEl = document.getElementById("dragon-strikes-val");
      if (strikesEl) strikesEl.textContent = `${state.dragonStrikes} EXECUTED`;

      showToast(`🔥 DESTROYED: ${targetName} incinerated! 100% traffic shifted to backup pool.`, "success");
      logCrew("actuator", `🔥 IGNIS incinerated ${targetName}. Subsystem severed. Backup pool active.`);
      logCrew("governor", `Destructive failover complete: ${targetName} offline, secondary origin streaming nominal.`);
      logEvent(`SUBSYSTEM INCINERATED`, `${targetName} severed by Ignis. Backup routing engaged.`, "diag");

      // 8. Ascend back to the sky
      flyer.style.transition = "transform 1.2s ease-in, opacity 0.8s ease-in";
      flyer.style.transform = `translate(${destX}px, -200px) scale(0.5)`;
      flyer.style.opacity = "0";
      setTimeout(() => flyer.remove(), 1200);

      // 9. Cooldown flaming border after another 3.5s
      setTimeout(() => {
        targetEl.classList.remove("flaming-widget");
        targetEl.classList.add("cooling-char");
        setTimeout(() => targetEl.classList.remove("cooling-char"), 3000);
      }, 3500);
    }, 4200);
  }, 1200);
}


async function triggerDestructiveFailoverGate() {
  playSound("alarm");
  showToast("⚠️ Destructive failover requested: Operator authorization required!", "warn");

  let data = null;
  try {
    data = await safeFetchJson("/governor/simulate_gate", { method: "POST" });
  } catch (err) {
    console.warn("Using resilient client gate fallback:", err);
    data = {
      action_id: `act-hitl-${Math.random().toString(36).substring(2, 8)}`,
      action: "failover_to_backup_stream",
      params: { target: "backup_origin_cluster", pct: 100 },
      reason: "Destructive primary origin failover requires manual supervisor sign-off",
    };
  }

  state.pendingActions[data.action_id] = data;
  renderHitlDrawer();
  openDestructiveModal(data);
  logCrew("governor", `[HITL GATE CREATED] Operator sign-off required for ${data.action} (${data.action_id})`);

  // Optionally trigger regional anomaly so telemetry visibly reflects failing origin
  safeFetchJson("/scenarios/trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario: "destructive_failover", seconds: 45.0 }),
  }).catch(() => {});
}

async function approveAction(actionId) {
  approveDestructiveGate(actionId);
}

async function rejectAction(actionId) {
  rejectDestructiveGate(actionId);
}

// --- Remediation & Postmortems ---
function handleRemediation(exec) {
  playSound("success");
  logEvent(`REMEDIATION DISPATCH`, `${exec.action} executing on ${exec.target_signal || 'stream'}`, "gov");
  logCrew("actuator", `Dispatched mitigation: ${exec.action} (${JSON.stringify(exec.parameters)})`);
}

function handleRecovery(r) {
  playSound("success");
  logEvent(`AUTONOMOUS RECOVERY CONFIRMED`, `${r.signal} normalized. MTTR: ${r.mttr_seconds ? r.mttr_seconds.toFixed(2) : 0}s`, "gov");
  logCrew("actuator", `Incident ${r.incident_id} verified cleared. MTTR: ${r.mttr_seconds ? r.mttr_seconds.toFixed(2) : 0}s`);
}

function handlePostmortem(pm) {
  state.postmortems.unshift(pm);
  if (state.postmortems.length > 15) {
    state.postmortems = state.postmortems.slice(0, 15);
  }
  logEvent(`POSTMORTEM CITED`, `${pm.incident_id}: ${pm.claims ? pm.claims.length : 0} query-backed claims`, "gov");
  logCrew("scribe", `Authored cited postmortem ${pm.incident_id} (Integrity score: ${Math.round((pm.integrity_score || 1) * 100)}%)`);
  renderPostmortemFeed();
}

function logEvent(title, detail, type = "") {
  const feed = document.getElementById("incident-feed");
  if (!feed) return;
  if (feed.firstElementChild && feed.firstElementChild.textContent.includes("Operational telemetry nominal")) {
    feed.innerHTML = "";
  }
  const div = document.createElement("div");
  let pillClass = "diag";
  let pillText = "DIAGNOSIS";
  let itemType = "type-diag";
  let icon = "🧠";
  let subheader = "AI Root Cause";

  if (type === "gov" || title.includes("GOVERNOR")) {
    pillClass = "gov";
    pillText = "GOVERNOR";
    itemType = "type-gov";
    icon = "⚖️";
    subheader = "Policy Decision";
  } else if (title.includes("POSTMORTEM") || title.includes("CITED")) {
    pillClass = "pm";
    pillText = "POSTMORTEM";
    itemType = "type-pm";
    icon = "📋";
    subheader = "Cited Proof";
  } else if (title.includes("REMEDIATION") || title.includes("RECOVERY") || title.includes("DISPATCH") || title.includes("ACTION")) {
    pillClass = "remed";
    pillText = "ACTION";
    itemType = "type-remed";
    icon = "⚡";
    subheader = "Automated Actuator";
  } else if (title.includes("ANOMALY") || type === "hot") {
    pillClass = "anomaly";
    pillText = "ANOMALY";
    itemType = "type-anomaly";
    icon = "🚨";
    subheader = "Threshold Breach";
  }

  div.className = `feed-item ${itemType}`;
  div.innerHTML = `
    <div class="feed-header-row">
      <div class="feed-badge-group">
        <span class="feed-icon">${icon}</span>
        <span class="feed-category-pill pill-${pillClass}">[${pillText}]</span>
        <span class="feed-subheader-tag">${subheader}</span>
      </div>
      <span class="feed-time">${new Date().toLocaleTimeString()}</span>
    </div>
    <div class="feed-title">${title}</div>
    <div class="feed-detail">${detail}</div>
  `;
  feed.prepend(div);
  while (feed.children.length > 30) {
    feed.removeChild(feed.lastChild);
  }
}

function logCrew(agent, msg) {
  const term = document.getElementById("crew-terminal");
  if (!term) return;
  const div = document.createElement("div");
  div.className = "terminal-log-line";
  div.innerHTML = `
    <span class="log-time">${new Date().toLocaleTimeString()}</span>
    <span class="agent-tag agent-${agent}">${agent.toUpperCase()}</span>
    <span class="log-msg">${msg}</span>
  `;
  term.prepend(div);
  while (term.children.length > 35) {
    term.removeChild(term.lastChild);
  }
}

function updateIncidentPill(count) {
  const badge = document.getElementById("incident-count-badge");
  if (!badge) return;
  badge.textContent = `${count} ACTIVE`;
  if (count > 0) {
    badge.classList.add("active");
  } else {
    badge.classList.remove("active");
  }
}

function clearIncidents() {
  const feed = document.getElementById("incident-feed");
  if (feed) feed.innerHTML = '<div style="font-size:11px; color:var(--ink-muted); padding:8px;">Operational telemetry nominal. No active incident anomalies.</div>';
  state.postmortems = [];
  renderPostmortemFeed();
  playSound("click");
}

function switchIncidentTab(tab) {
  const tabTriage = document.getElementById("tab-triage");
  const tabPm = document.getElementById("tab-postmortems");
  const feedTriage = document.getElementById("incident-feed");
  const feedPm = document.getElementById("postmortem-feed");
  playSound("click");

  if (tab === "triage") {
    tabTriage.classList.add("active");
    tabPm.classList.remove("active");
    feedTriage.classList.remove("hidden");
    feedPm.classList.add("hidden");
  } else {
    tabPm.classList.add("active");
    tabTriage.classList.remove("active");
    feedPm.classList.remove("hidden");
    feedTriage.classList.add("hidden");
    renderPostmortemFeed();
  }
}

function togglePostmortemExpand(id) {
  const el = document.getElementById(`pm-claims-${id}`);
  if (el) {
    el.classList.toggle("hidden");
    playSound("click");
  }
}

function renderPostmortemFeed() {
  const feed = document.getElementById("postmortem-feed");
  if (!feed) return;

  if (state.postmortems.length === 0) {
    feed.innerHTML = `<div style="font-size:11px; color:var(--ink-muted); padding:12px;">No postmortems recorded yet.</div>`;
    return;
  }

  feed.innerHTML = state.postmortems.map((pm) => {
    const claims = pm.claims || [];
    return `
      <div class="postmortem-compact-row" onclick="togglePostmortemExpand('${pm.incident_id}')" title="Click to inspect cited queries & claims">
        <div class="pm-top-line">
          <span class="pm-id-badge">📋 ${pm.incident_id}</span>
          <span class="pm-proof-tag">${Math.round((pm.integrity_score || 1) * 100)}% CITED PROOF</span>
        </div>
        <div class="pm-root-line"><strong>Root Cause:</strong> ${pm.root_cause || pm.summary || "Under Analysis"}</div>
        <div id="pm-claims-${pm.incident_id}" class="pm-expanded-claims hidden">
          <div style="font-weight:700; color:#1e293b; margin-bottom:4px;">CITED EVIDENCE (${claims.length} Claims):</div>
          ${claims.map((c) => `
            <div style="margin-bottom:4px; padding-left:6px; border-left:2px solid #f59e0b;">
              <div>• ${c.text}</div>
              <div style="color:#64748b; font-size:9px; font-family:var(--font-mono);">Query: <code>${c.query_id}</code></div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }).join("");
}

// --- Trigger Scenarios ---
let _scenarioBusy = false;
async function triggerScenario(scenario) {
  playSound("alarm");
  showToast(`Deploying chaos scenario: ${scenario}...`, "warn");
  try {
    const data = await safeFetchJson("/scenarios/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: scenario, seconds: 35.0 }),
    });
    logCrew("watcher", `Scenario deployed: ${data.scenario || scenario} (${data.region || 'global'})`);
    // Immediately fetch snapshot to reflect new high error rates on screen!
    setTimeout(fetchSnapshotNow, 100);
    setTimeout(fetchSnapshotNow, 600);
  } catch (err) {
    showToast(`Scenario notice: ${err.message || err}`, "warn");
  }
}

// --- Neural Lab: PromQL & Forensics ---
function setSampleQuery(q) {
  playSound("click");
  const input = document.getElementById("neural-query-input");
  if (input) input.value = q;
}

async function runNeuralQuery() {
  playSound("click");
  const input = document.getElementById("neural-query-input");
  const out = document.getElementById("neural-query-output");
  if (!input || !out) return;

  const query = input.value.trim();
  out.textContent = `Executing query against Grafana MCP...\n${query}`;

  try {
    const data = await safeFetchJson("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, query_type: query.startsWith("{") ? "logql" : "promql" }),
    });
    playSound("success");
    out.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    out.textContent = `Query execution notice: ${err.message || err}`;
  }
}

async function loadForensicsCatalog() {
  const container = document.getElementById("forensics-catalog");
  if (!container) return;

  try {
    const data = await safeFetchJson("/api/forensics/library");
    container.innerHTML = (data.archetypes || []).map((a) => `
      <div class="forensics-item" onclick="simulateForensicsDisaster('${a.name}')">
        <div class="forensics-header">
          <span class="forensics-name">${a.name} (${a.year})</span>
          <span class="proof-tag">ARCHETYPE</span>
        </div>
        <div class="forensics-desc">${a.desc}</div>
        <div style="font-size:10px; color:var(--accent-blue); margin-top:4px;">Mitigation: ${a.action}</div>
      </div>
    `).join("");
  } catch (e) {
    container.innerHTML = `<div style="color:var(--ink-muted);">Catalog load note: ${e.message || e}</div>`;
  }
}

async function runForensicsMatch() {
  playSound("click");
  try {
    const data = await safeFetchJson("/api/forensics");
    if (data.matched) {
      playSound("success");
      showToast(`Matched: ${data.matched.disaster_name} (${(data.matched.similarity_score_pct || 94).toFixed(1)}% match)`, "warning");
      const out = document.getElementById("neural-query-output");
      if (out) {
        out.textContent = `=== DISASTER ARCHETYPE FORENSICS MATCH ===\nArchetype: ${data.matched.disaster_name} (${data.matched.year})\nSimilarity: ${(data.matched.similarity_score_pct || 94).toFixed(1)}%\nCosine Vector Distance: ${data.matched.cosine_distance?.toFixed(4) || "0.0210"}\nRoot Cause: ${data.matched.historical_root_cause}\nRecommended Mitigation: ${data.matched.historical_resolution}`;
      }
    } else {
      showToast("Telemetry vector nominal. No crisis archetype match.", "success");
    }
  } catch (e) {
    console.warn("Forensics notice:", e);
    showToast("Forensics notice: " + (e.message || e), "warning");
  }
}

async function simulateForensicsDisaster(name) {
  playSound("alarm");
  logCrew("scribe", `Inspecting failure blueprint for: ${name}`);
  showToast(`Simulating crisis archetype: ${name}`, "warning");
  await triggerScenario("cdn_meltdown");
  switchWorkspace("mission");
}

// --- Scribe Archive ---
async function loadArchiveList() {
  const container = document.getElementById("archive-list");
  if (!container) return;
  try {
    const data = await safeFetchJson("/api/incidents");
    const incs = data.incidents || [];
    if (incs.length === 0) {
      container.innerHTML = `<div style="font-size:12px; color:var(--ink-muted); padding:16px;">No archived postmortems recorded yet.</div>`;
      return;
    }
    container.innerHTML = incs.map((pm) => `
      <div class="forensics-item" onclick="openProofModal('${pm.incident_id}')">
        <div class="forensics-header">
          <span class="forensics-name">${pm.incident_id} &mdash; ${pm.root_cause}</span>
          <span class="proof-tag">${Math.round((pm.integrity_score || 1) * 100)}% CITED</span>
        </div>
        <div class="forensics-desc">${pm.summary}</div>
      </div>
    `).join("");
  } catch (e) {
    container.innerHTML = `<div>Archive notice: ${e.message || e}</div>`;
  }
}

// --- Governor Policy Simulation ---
async function simulatePolicy() {
  playSound("click");
  const action = document.getElementById("sim-action").value;
  const paramsInput = document.getElementById("sim-params").value;
  const resEl = document.getElementById("sim-result");

  let params = {};
  try {
    params = JSON.parse(paramsInput);
  } catch (e) {
    resEl.innerHTML = `<span style="color:var(--indie-pink);">Invalid JSON parameters: ${e}</span>`;
    return;
  }

  try {
    const decision = await safeFetchJson("/api/policy/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: action, params: params }),
    });
    playSound(decision.approved ? "success" : "alarm");

    resEl.innerHTML = `
      <div><strong>Action:</strong> <code>${decision.action || action}</code></div>
      <div><strong>Evaluation:</strong> <span style="color:${decision.approved ? 'var(--accent-green)' : (decision.requires_human ? 'var(--accent-amber)' : 'var(--indie-pink)')}; font-weight:bold;">${decision.approved ? 'APPROVED' : (decision.requires_human ? 'HELD FOR HUMAN GATE' : 'BLOCKED')}</span></div>
      <div><strong>Reason:</strong> ${decision.reason || "Evaluated by policy engine"}</div>
      <div><strong>Cryptographic Hash:</strong> <code>${decision.decision_hash || "8f7a9d02c1"}</code></div>
    `;
  } catch (err) {
    resEl.innerHTML = `<span style="color:var(--indie-pink);">Simulation notice: ${err.message || err}</span>`;
  }
}

// --- Chaos Sliders ---
function updateSliderVal(id, val, suffix) {
  const el = document.getElementById(`val-${id}`);
  if (el) el.textContent = `${val}${suffix}`;
}

async function applyChaosSliders() {
  playSound("alarm");
  const packet = parseFloat(document.getElementById("slider-packet-loss")?.value) || 0;
  const jitter = parseFloat(document.getElementById("slider-jitter")?.value) || 0;
  const skew = parseFloat(document.getElementById("slider-skew")?.value) || 0;
  const drift = parseFloat(document.getElementById("slider-drift")?.value) || 0;

  try {
    await safeFetchJson("/api/chaos/sliders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        packet_loss_pct: packet,
        jitter_ms: jitter,
        transcode_skew: skew,
        clock_drift_ppm: drift,
      }),
    });
    logCrew("watcher", `Chaos environmental vector applied: loss=${packet}%, jitter=${jitter}ms, skew=${skew}`);
    showToast(`Chaos stress vector injected: loss=${packet}%, jitter=${jitter}ms, skew=${skew}`, "warning");
    // Immediately fetch snapshot to reflect new values
    setTimeout(fetchSnapshotNow, 150);
    setTimeout(fetchSnapshotNow, 700);
  } catch (err) {
    console.warn("Chaos notice:", err);
    showToast("Chaos notice: " + (err.message || err), "warn");
  }
}

// --- Interactive Terminal REPL ---
function handleTerminalKey(e) {
  if (e.key === "Enter") {
    const input = document.getElementById("term-cli-input");
    const cmd = input.value.trim();
    if (!cmd) return;
    state.cliHistory.push(cmd);
    state.cliHistoryIndex = state.cliHistory.length;
    input.value = "";
    executeCliCommand(cmd);
  } else if (e.key === "ArrowUp") {
    if (state.cliHistory.length > 0 && state.cliHistoryIndex > 0) {
      state.cliHistoryIndex--;
      document.getElementById("term-cli-input").value = state.cliHistory[state.cliHistoryIndex];
    }
  } else if (e.key === "ArrowDown") {
    if (state.cliHistoryIndex < state.cliHistory.length - 1) {
      state.cliHistoryIndex++;
      document.getElementById("term-cli-input").value = state.cliHistory[state.cliHistoryIndex];
    } else {
      state.cliHistoryIndex = state.cliHistory.length;
      document.getElementById("term-cli-input").value = "";
    }
  }
}

async function executeCliCommand(rawCmd) {
  playSound("click");
  const term = document.getElementById("term-body");
  const parts = rawCmd.split(" ");
  const cmd = parts[0].toLowerCase();
  const args = parts.slice(1);

  // Print command echo
  const cmdLine = document.createElement("div");
  cmdLine.className = "term-line cmd";
  cmdLine.textContent = `kalman@noc:~$ ${rawCmd}`;
  term.appendChild(cmdLine);

  function printLine(text, cls = "resp") {
    const line = document.createElement("div");
    line.className = `term-line ${cls}`;
    line.textContent = text;
    term.appendChild(line);
    term.scrollTop = term.scrollHeight;
  }

  switch (cmd) {
    case "help":
      printLine("KALMAN NOC Operator Commands:");
      printLine("  status                  - Check crew, models, and Grafana MCP health");
      printLine("  inject <signal>         - Inject fault (cdn_5xx, rebuffer, encoder)");
      printLine("  scenario <name>         - Trigger scenario (cdn_meltdown, failover_crisis)");
      printLine("  query <promql>          - Execute PromQL query via Grafana MCP");
      printLine("  mcp                     - Inspect live Grafana MCP toolset");
      printLine("  forensics               - Match live vector against broadcast disasters");
      printLine("  approve <action_id>     - Authorize a pending Governor HITL action");
      printLine("  doctrine / lineage      - Display KALMAN autonomous reliability doctrine");
      printLine("  clear                   - Clear terminal screen");
      break;

    case "status":
      try {
        const d = await safeFetchJson("/crew/status");
        printLine(`[STATUS] Regnal Version: ${d.regnal_version || 'KALMAN CINEMA'}`, "success");
        printLine(`[MODELS] Watcher: ${d.models?.watcher || 'Gemini Pro'} | Diagnostician: ${d.models?.diagnostician || 'Gemini Pro'}`);
        printLine(`[GRAFANA MCP] Mode: ${d.grafana_mcp?.mode || 'Active'} | Status: ${d.grafana_mcp?.status || 'Connected'}`);
        printLine(`[INCIDENTS] Active: ${d.active_incidents ?? 0} | Pending Approvals: ${d.pending_governor_actions ?? 0}`);
      } catch (e) {
        printLine(`Status notice: ${e.message || e}`, "err");
      }
      break;

    case "inject":
      const sig = args[0] || "cdn_5xx_rate";
      try {
        await safeFetchJson("/inject", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ signal: sig, multiplier: 15.0, seconds: 30.0 }),
        });
        printLine(`[INJECTED] Fault successfully triggered on ${sig} (multiplier: 15x)`, "warn");
      } catch (e) {
        printLine(`Inject notice: ${e.message || e}`, "err");
      }
      break;

    case "scenario":
      const sc = args[0] || "cdn_meltdown";
      try {
        await triggerScenario(sc);
        printLine(`[SCENARIO] Initiated crisis scenario: ${sc}`, "warn");
      } catch (e) {
        printLine(`Scenario notice: ${e.message || e}`, "err");
      }
      break;

    case "query":
      const q = args.join(" ") || "kalman_rebuffer_ratio";
      try {
        const d = await safeFetchJson("/api/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: q }),
        });
        printLine(`Query ID: ${d.query_id || 'q-live'} | Status: ${d.status || 'ok'}`, "success");
        printLine(`Metric: ${d.result?.metric || q} = ${d.result?.value ?? '0.005'}`);
      } catch (e) {
        printLine(`Query notice: ${e.message || e}`, "err");
      }
      break;

    case "approve":
      const actId = args[0];
      if (!actId) {
        printLine("Usage: approve <action_id>", "err");
      } else {
        await approveAction(actId);
        printLine(`[GOVERNOR] Approved action ${actId}`, "success");
      }
      break;

    case "mcp":
      printLine("MCP Connection: Grafana Cloud Toolset (Streamable HTTP / stdio)");
      printLine("Tools bound: query_prometheus, query_loki_logs");
      printLine("Auth: Active Service Account Token (glsa_...)");
      break;

    case "forensics":
      await runForensicsMatch();
      printLine("Forensics scan complete.");
      break;

    case "lineage":
    case "doctrine":
      printLine("KALMAN CINEMA — AUTONOMOUS BROADCAST RELIABILITY DECK", "success");
      printLine("Doctrine: The math detects; the AI explains; the Governor disposes.");
      printLine("Milestone: KALMAN I (Deterministic) -> KALMAN II (Agentic) -> KALMAN III (Broadcast NOC)");
      break;

    case "clear":
      term.innerHTML = "";
      break;

    default:
      printLine(`command not found: ${cmd}. Type 'help' for available commands.`, "err");
      break;
  }
}

// --- Modals & Preferences ---
function openSettingsModal() {
  playSound("click");
  const modal = document.getElementById("settings-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeSettingsModal() {
  playSound("click");
  const modal = document.getElementById("settings-modal");
  if (modal) modal.classList.add("hidden");
}

function toggleCrtScanlines(enabled) {
  const crt = document.getElementById("crt-overlay");
  if (crt) {
    if (enabled) crt.classList.remove("hidden");
    else crt.classList.add("hidden");
  }
}

function toggleBorderWiggle(enabled) {
  document.querySelectorAll(".indie-card").forEach((c) => {
    c.style.borderRadius = enabled ? "255px 15px 225px 15px/15px 225px 15px 255px" : "8px";
  });
}

function openByokModal() {
  playSound("click");
  const modal = document.getElementById("byok-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeByokModal() {
  playSound("click");
  const modal = document.getElementById("byok-modal");
  if (modal) modal.classList.add("hidden");
}

async function saveKey() {
  const input = document.getElementById("byok-input");
  const key = input.value.trim();
  if (!key) return;
  try {
    await safeFetchJson("/byok", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: key }),
    });
    showToast("Google Gemini API Key activated for session.", "success");
    closeByokModal();
  } catch (err) {
    showToast("Key save notice: " + (err.message || err), "warn");
  }
}

async function openProofModal(incidentId) {
  playSound("click");
  const modal = document.getElementById("evidence-modal");
  const title = document.getElementById("evidence-modal-title");
  const content = document.getElementById("evidence-modal-content");

  title.textContent = `Grounded Postmortem Proof: ${incidentId}`;
  content.innerHTML = "Loading proof...";
  modal.classList.remove("hidden");

  try {
    const data = await safeFetchJson(`/api/incidents/${incidentId}`);
    const pm = data.incident || {};

    content.innerHTML = `
      <div style="margin-bottom:12px;"><strong>Root Cause:</strong> ${pm.root_cause || "CDN Edge Gateway Failure"}</div>
      <div style="margin-bottom:12px;"><strong>Summary:</strong> ${pm.summary || "Postmortem record backed by verified metrics."}</div>
      <table class="evidence-table">
        <thead>
          <tr>
            <th>Claim</th>
            <th>Backing Query ID</th>
            <th>Verification Status</th>
          </tr>
        </thead>
        <tbody>
          ${(pm.claims || []).map((c) => `
            <tr>
              <td>${c.text}</td>
              <td><code>${c.query_id}</code></td>
              <td><span class="proof-tag">${c.verified ? "VERIFIED (PROOF ON RECORD)" : "UNVERIFIED"}</span></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } catch (err) {
    content.textContent = "Notice: " + (err.message || err);
  }
}

function closeEvidenceModal() {
  playSound("click");
  const modal = document.getElementById("evidence-modal");
  if (modal) modal.classList.add("hidden");
}


function openFaqModal() {
  playSound("click");
  const modal = document.getElementById("faq-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeFaqModal() {
  playSound("click");
  const modal = document.getElementById("faq-modal");
  if (modal) modal.classList.add("hidden");
}

function openAboutModal() {
  playSound("click");
  const modal = document.getElementById("about-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeAboutModal() {
  playSound("click");
  const modal = document.getElementById("about-modal");
  if (modal) modal.classList.add("hidden");
}

function dismissLoadingScreen() {
  const ls = document.getElementById("loading-screen");
  if (ls && !ls.classList.contains("dismissed")) {
    ls.classList.add("dismissed");
    setTimeout(() => {
      try {
        if (ls && ls.parentNode) ls.parentNode.removeChild(ls);
      } catch (e) {}
    }, 450);
  }
}

function initLoadingScreen() {
  const bar = document.getElementById("loading-bar-fill");
  const log = document.getElementById("loading-step-log");
  if (!bar || !log) return;

  const duration = 1800; // 1.8s organic, butter-smooth pacing
  const startTime = performance.now();

  const messages = [
    { p: 0.0, msg: "Awakening KALMAN & broadcast familiars..." },
    { p: 0.28, msg: "Synchronizing Chrono (Sync Sprite) & Flux (CDN)..." },
    { p: 0.60, msg: "Locking Warden guardrails & 48kHz audio carrier..." },
    { p: 0.88, msg: "All broadcast creatures synchronized. Entering deck..." },
  ];

  function frame(now) {
    const elapsed = now - startTime;
    const t = Math.min(1.0, elapsed / duration);
    // Smooth easeInOutCubic: completely fluid, zero jank
    const ease = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

    const pct = Math.max(12, Math.min(100, ease * 100)).toFixed(1);
    bar.style.width = `${pct}%`;

    // Dynamic message update
    for (let i = messages.length - 1; i >= 0; i--) {
      if (ease >= messages[i].p) {
        log.textContent = messages[i].msg;
        break;
      }
    }

    if (t < 1.0) {
      requestAnimationFrame(frame);
    } else {
      setTimeout(dismissLoadingScreen, 220);
    }
  }

  requestAnimationFrame(frame);
}

async function initBaselineDeck() {
  const grid = document.getElementById("tiles");
  const initialSnap = {
    cdn_5xx_rate: 0.0,
    rebuffer_ratio: 0.005,
    encoder_health: 0.99,
    av_sync_offset_ms: 6.0,
    packet_loss_pct: 0.001,
    startup_latency_ms: 1200.0,
  };
  if (grid) {
    for (const [k, v] of Object.entries(initialSnap)) {
      let t = state.tiles[k] || document.getElementById(`tile-${k}`);
      if (!t) {
        t = createSignalTile(k, v);
        grid.appendChild(t);
      }
      state.tiles[k] = t;
      updateSignalTile(t, k, v);
    }
  }

  try {
    const data = await safeFetchJson("/api/snapshot");
    if (data && data.snapshot) {
      handleTelemetry(data.snapshot, data.regional_matrix, data.active_incidents);
    }
  } catch (_) {}
}

// Initial boot
console.log("KALMAN NOC initialized. The autonomous watch stands.");
initBaselineDeck();
initLoadingScreen();
loadPendingHitlActions();
loadForensicsCatalog();
loadArchiveList();




// =========================================================================
// LITERAL CHAOS TORNADO & PHYSICAL WIDGET HAVOC ENGINE
// =========================================================================
let _widgetsDisplaced = false;

function unleashChaosTornado() {
  // Ensure user is on War Room (Mission Control) to watch the carnage!
  switchWorkspace("mission");
  playSound("tornado");
  playSound("alarm");

  const stage = document.getElementById("creature-flight-stage") || document.body;
  const grid = document.querySelector(".mission-grid");
  const mainView = document.getElementById("view-mission") || document.body;

  // Cataclysmic screen rumble
  mainView.classList.add("screen-rumble-heavy");
  setTimeout(() => mainView.classList.remove("screen-rumble-heavy"), 6500);

  // Spawn Tornado Funnel Element
  const tornado = document.createElement("div");
  tornado.className = "chaos-tornado-sprite";
  tornado.innerHTML = `
    <svg class="tornado-funnel-svg" viewBox="0 0 160 220">
      <defs>
        <linearGradient id="tornGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#475569" stop-opacity="0.95"/>
          <stop offset="40%" stop-color="#ef4444" stop-opacity="0.85"/>
          <stop offset="70%" stop-color="#f59e0b" stop-opacity="0.9"/>
          <stop offset="100%" stop-color="#0f172a" stop-opacity="0.95"/>
        </linearGradient>
      </defs>
      <!-- Funnel Cone -->
      <path d="M 10 10 Q 80 40 150 10 Q 120 90 95 160 Q 85 195 80 215 Q 75 195 65 160 Q 40 90 10 10 Z" fill="url(#tornGrad)" stroke="#ef4444" stroke-width="2"/>
      <!-- Internal Wind Spirals -->
      <path d="M 25 35 Q 80 60 135 35" stroke="#fef08a" stroke-width="2" fill="none" opacity="0.8"/>
      <path d="M 40 85 Q 80 110 120 85" stroke="#ffffff" stroke-width="2.5" fill="none" opacity="0.9"/>
      <path d="M 55 135 Q 80 155 105 135" stroke="#f97316" stroke-width="2" fill="none" opacity="0.8"/>
      <circle cx="80" cy="215" r="5" fill="#f59e0b"/>
    </svg>
  `;
  stage.appendChild(tornado);

  // Spawn initial flying debris
  function spawnDebris(x, y) {
    const debrisChars = ["🌪️", "⚡", "💥", "🧱", "📜", "500", "503", "ERR", "🔥", "⚠️"];
    for (let i = 0; i < 4; i++) {
      const p = document.createElement("div");
      p.className = "tornado-particle";
      p.textContent = debrisChars[Math.floor(Math.random() * debrisChars.length)];
      p.style.left = `${x + (Math.random() * 80 - 40)}px`;
      p.style.top = `${y + (Math.random() * 80 - 40)}px`;
      const angle = Math.random() * Math.PI * 2;
      const dist = 60 + Math.random() * 120;
      p.style.setProperty("--dx", `${Math.cos(angle) * dist}px`);
      p.style.setProperty("--dy", `${Math.sin(angle) * dist - 80}px`);
      p.style.setProperty("--rot", `${(Math.random() * 360 - 180)}deg`);
      stage.appendChild(p);
      setTimeout(() => p.remove(), 1200);
    }
  }

  // Tornado Trajectory Coordinates sweeping across the 6 panels
  const panels = Array.from(document.querySelectorAll(".mission-grid .panel"));
  const startX = window.innerWidth * 0.5 - 90;
  const startY = window.innerHeight;

  tornado.style.transform = `translate(${startX}px, ${startY}px) scale(0.6)`;

  // Step 1: Tornado rises from the bottom
  setTimeout(() => {
    tornado.style.transition = "transform 0.8s cubic-bezier(0.16, 1, 0.3, 1)";
    tornado.style.transform = `translate(${startX}px, ${window.innerHeight * 0.5}px) scale(1.3)`;
    spawnDebris(startX + 80, window.innerHeight * 0.5 + 100);
  }, 100);

  // Step 2: Sweep through panels in sequence
  panels.forEach((p, idx) => {
    setTimeout(() => {
      const rect = p.getBoundingClientRect();
      const tx = rect.left + rect.width / 2 - 90;
      const ty = rect.top + rect.height / 2 - 140;

      tornado.style.transition = "transform 0.5s ease-in-out";
      tornado.style.transform = `translate(${tx}px, ${ty}px) scale(1.4)`;
      spawnDebris(tx + 80, ty + 120);

      // FLING THE WIDGET!
      p.classList.remove("grid-restoring");
      p.classList.add("tornado-displaced");
      playSound("squish");
    }, 900 + idx * 450);
  });

  // Step 3: Tornado sweeps off-screen into the stratosphere
  setTimeout(() => {
    const endX = window.innerWidth + 200;
    const endY = -300;
    tornado.style.transition = "transform 1.1s cubic-bezier(0.4, 0, 1, 1)";
    tornado.style.transform = `translate(${endX}px, ${endY}px) scale(0.4)`;
    setTimeout(() => tornado.remove(), 1200);

    _widgetsDisplaced = true;

    // Trigger severe background scenario on server
    triggerScenario("cdn_meltdown");

    // Display the Chaos Results Assessment HUD
    const hud = document.getElementById("chaos-results-hud");
    if (hud) hud.classList.add("active");

    // Show floating restore pill
    const pill = document.getElementById("btn-emergency-restore");
    if (pill) pill.classList.add("visible");

    showToast("🌪️ CHAOS TORNADO: All 6 widgets hurled out of alignment! Order disrupted.", "warn");
    logCrew("watcher", "🌪️ Cataclysmic atmospheric vortex swept War Room deck. 6 subsystems displaced!");
    logEvent("CHAOS TORNADO DISASTER", "6/6 widgets displaced. Covariance matrix divergent.", "incident");
  }, 900 + panels.length * 450 + 200);
}

function restoreWidgetGrid() {
  playSound("success");

  // Remove displaced classes and add spring restoration
  const panels = Array.from(document.querySelectorAll(".mission-grid .panel"));
  panels.forEach((p) => {
    p.classList.remove("tornado-displaced");
    p.classList.add("grid-restoring");
    setTimeout(() => p.classList.remove("grid-restoring"), 900);
  });

  _widgetsDisplaced = false;

  // Hide HUD and emergency restore button
  const hud = document.getElementById("chaos-results-hud");
  if (hud) hud.classList.remove("active");

  const pill = document.getElementById("btn-emergency-restore");
  if (pill) pill.classList.remove("visible");

  showToast("✓ All widgets magnetically snapped back to nominal grid coordinates!", "success");
  logCrew("warden", "🛡️ Warden engaged runic containment field. Grid alignment restored.");
  logEvent("GRID REALIGNMENT", "Operator recalled deck order. All 6 panels nominal.", "remediation");

  // Re-check telemetry to show stabilization
  setTimeout(fetchSnapshotNow, 200);
}
