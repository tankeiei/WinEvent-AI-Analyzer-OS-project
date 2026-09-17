/**
 * WinEvent Analyzer - Frontend Application Controller
 * Handles live telemetry fetching, interactive search/filtering, and simulation triggers.
 */

const API_BASE = "";

// Application State
const state = {
  events: [],
  selectedEvent: null,
  currentType: "ALL",
  currentHours: 48,
  searchQuery: "",
  isLoading: false,
};

// DOM Elements
const elements = {
  systemHost: document.getElementById("sys-host"),
  systemEngine: document.getElementById("sys-engine"),
  timelineList: document.getElementById("timeline-list"),
  detailContainer: document.getElementById("detail-container"),
  eventCount: document.getElementById("event-count"),
  timeFilter: document.getElementById("time-filter"),
  searchInput: document.getElementById("search-input"),
  btnRefresh: document.getElementById("btn-refresh"),
  tabButtons: document.querySelectorAll(".tab-btn"),
  simButtons: document.querySelectorAll(".btn-sim"),
  toastContainer: document.getElementById("toast-container"),
};

// Initialize Application
async function initApp() {
  setupEventListeners();
  await loadSystemInfo();
  await loadEvents();
}

// Event Listeners
function setupEventListeners() {
  // Time window filter change
  elements.timeFilter.addEventListener("change", (e) => {
    state.currentHours = parseInt(e.target.value);
    loadEvents();
  });

  // Search input live filtering
  elements.searchInput.addEventListener("input", (e) => {
    state.searchQuery = e.target.value.toLowerCase().trim();
    applyFilters();
  });

  // Refresh button
  elements.btnRefresh.addEventListener("click", () => {
    loadEvents();
  });

  // Type filter tabs (ALL / CRASH / HANG)
  elements.tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      elements.tabButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.currentType = btn.dataset.type;
      applyFilters();
    });
  });

  // Simulation Trigger Buttons
  elements.simButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const simType = btn.dataset.sim;
      triggerSimulation(simType);
    });
  });
}

// Fetch Host Environment Info
async function loadSystemInfo() {
  try {
    const res = await fetch(`${API_BASE}/api/system-info`);
    if (!res.ok) return;
    const info = await res.json();
    if (elements.systemHost) elements.systemHost.textContent = info.machine_name || "Windows PC";
    if (elements.systemEngine) elements.systemEngine.textContent = info.engine_mode || "PowerShell";
  } catch (err) {
    console.warn("Could not load system info:", err);
  }
}

// Fetch Events from Backend
async function loadEvents() {
  state.isLoading = true;
  renderLoading();

  try {
    const res = await fetch(`${API_BASE}/api/events?hours=${state.currentHours}&limit=100&type=ALL`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    
    state.events = data.events || [];
    applyFilters();
    
    showToast(`Loaded ${state.events.length} telemetry event(s)`, "info");
  } catch (err) {
    renderError(`Failed to connect to Windows Event Log: ${err.message}`);
    showToast("Error loading event logs", "error");
  } finally {
    state.isLoading = false;
  }
}

// Apply Client-Side Filters
function applyFilters() {
  const filtered = state.events.filter((e) => {
    // Type Filter
    if (state.currentType !== "ALL" && e.event_type !== state.currentType) {
      return false;
    }
    // Search Query (App Name, Module Name, Code)
    if (state.searchQuery) {
      const q = state.searchQuery;
      const matchApp = (e.app_name || "").toLowerCase().includes(q);
      const matchMod = (e.module_name || "").toLowerCase().includes(q);
      const matchCode = (e.exception_code || "").toLowerCase().includes(q);
      const matchSymbol = (e.exception_symbol || "").toLowerCase().includes(q);
      return matchApp || matchMod || matchCode || matchSymbol;
    }
    return true;
  });

  renderEventList(filtered);

  // Automatically select the first event if none or previous was lost
  if (filtered.length > 0) {
    if (!state.selectedEvent || !filtered.some(e => e.record_id === state.selectedEvent.record_id)) {
      selectEvent(filtered[0]);
    } else {
      renderEventDetail(state.selectedEvent);
    }
  } else {
    state.selectedEvent = null;
    renderEmptyDetail();
  }
}

// Render Left Panel Timeline List
function renderEventList(events) {
  elements.eventCount.textContent = `${events.length} events`;

  if (events.length === 0) {
    elements.timelineList.innerHTML = `
      <div class="empty-state">
        <p style="font-size: 1.5rem;">🔍</p>
        <p>No crash or hang events found matching criteria.</p>
        <small style="color: var(--text-dim)">Try increasing the time window or trigger a simulation above.</small>
      </div>
    `;
    return;
  }

  elements.timelineList.innerHTML = events
    .map((e, index) => {
      const isCrash = e.event_type === "CRASH";
      const isSelected = state.selectedEvent && state.selectedEvent.record_id === e.record_id;
      const timeFormatted = formatTime(e.time_created);
      const badgeClass = isCrash ? "badge-crash" : "badge-hang";
      const cardTypeClass = isCrash ? "card-crash" : "card-hang";
      const codeOrHang = isCrash ? e.exception_code : (e.hang_type || "HANG");

      return `
        <div class="event-card ${cardTypeClass} ${isSelected ? 'active' : ''}" data-index="${index}">
          <div class="card-top">
            <span class="badge ${badgeClass}">${e.event_type} (${e.event_id})</span>
            <span class="card-time">${timeFormatted}</span>
          </div>
          <div class="card-app-name" title="${e.app_name}">${e.app_name}</div>
          <div class="card-meta-row">
            <span class="card-code">${codeOrHang}</span>
            <span class="card-module" title="${e.module_name || ''}">${e.module_name || 'N/A'}</span>
          </div>
        </div>
      `;
    })
    .join("");

  // Attach click listeners
  elements.timelineList.querySelectorAll(".event-card").forEach((card, idx) => {
    card.addEventListener("click", () => {
      elements.timelineList.querySelectorAll(".event-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      selectEvent(events[idx]);
    });
  });
}

// Select and Display Event
function selectEvent(event) {
  state.selectedEvent = event;
  renderEventDetail(event);
}

// Render Right Panel Detailed OS Telemetry
function renderEventDetail(e) {
  if (!e) {
    renderEmptyDetail();
    return;
  }

  const isCrash = e.event_type === "CRASH";
  const typeBadgeClass = isCrash ? "badge-crash" : "badge-hang";
  const timeFormatted = formatTime(e.time_created);

  elements.detailContainer.innerHTML = `
    <div class="detail-header">
      <div class="detail-title-group">
        <h2>
          <span>${isCrash ? '💥' : '⏳'}</span>
          ${e.app_name}
          <span class="badge ${typeBadgeClass}">${e.event_type} • ID ${e.event_id}</span>
        </h2>
        <div class="detail-subtitle">
          Recorded: <strong>${timeFormatted}</strong> • Record ID: <code>${e.record_id || 'N/A'}</code>
        </div>
      </div>
    </div>

    <!-- Diagnostic Translation Callout -->
    <div class="explanation-card">
      <div class="explanation-tag">
        <span>📖</span> Diagnostic Interpretation (Tech-to-Human)
      </div>
      <div class="explanation-body">
        ${e.exception_meaning || 'No offline explanation available for this specific code.'}
      </div>
    </div>

    <!-- OS Telemetry Grid -->
    <div class="telemetry-grid">
      <div class="telemetry-item">
        <span class="telemetry-label">Exception / Identifier</span>
        <span class="telemetry-val" style="color: ${isCrash ? '#f87171' : '#fbbf24'}; font-weight: 700;">
          ${e.exception_code}
        </span>
      </div>

      <div class="telemetry-item">
        <span class="telemetry-label">Symbolic Name</span>
        <span class="telemetry-val">${e.exception_symbol || 'UNKNOWN'}</span>
      </div>

      <div class="telemetry-item">
        <span class="telemetry-label">Faulting Module</span>
        <span class="telemetry-val">${e.module_name || 'N/A'}</span>
      </div>

      <div class="telemetry-item">
        <span class="telemetry-label">Memory Fault Offset</span>
        <span class="telemetry-val">${e.fault_offset || 'N/A'}</span>
      </div>

      <div class="telemetry-item">
        <span class="telemetry-label">Process ID (PID)</span>
        <span class="telemetry-val">${e.process_id || 'N/A'}</span>
      </div>

      <div class="telemetry-item">
        <span class="telemetry-label">Application Version</span>
        <span class="telemetry-val">${e.app_version || '0.0.0.0'}</span>
      </div>

      ${e.hang_type ? `
      <div class="telemetry-item" style="grid-column: 1 / -1;">
        <span class="telemetry-label">Hang Classification</span>
        <span class="telemetry-val" style="color: #fbbf24;">${e.hang_type}</span>
      </div>` : ''}

      <div class="telemetry-item path-box">
        <span class="telemetry-label">Application Executable Path</span>
        <span class="telemetry-val">${e.app_path || 'Unknown Path'}</span>
      </div>

      ${e.module_path ? `
      <div class="telemetry-item path-box">
        <span class="telemetry-label">Module File Path</span>
        <span class="telemetry-val">${e.module_path}</span>
      </div>` : ''}

      <div class="telemetry-item path-box">
        <span class="telemetry-label">Telemetry Signature Hash (Cache Key)</span>
        <span class="telemetry-val" style="color: var(--accent-cyan); font-size: 0.8rem;">
          ${e.signature_hash}
        </span>
      </div>
    </div>

    <!-- Collapsible Raw JSON Viewer -->
    <div class="raw-json-section">
      <div class="raw-json-header" onclick="toggleRawJson()">
        <span>🛠️ Normalized JSON Payload (Pydantic Model)</span>
        <span id="raw-toggle-arrow">▼</span>
      </div>
      <pre id="raw-json-pre" class="raw-json-content">${escapeHtml(JSON.stringify(e, null, 2))}</pre>
    </div>
  `;
}

// Trigger Live Safe Simulation
async function triggerSimulation(simType) {
  showToast(`Triggering safe simulation: [${simType}]...`, "info");

  try {
    const res = await fetch(`${API_BASE}/api/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ simulation_type: simType }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Simulation failed");

    showToast(`Simulation completed! Windows recorded Event. Auto-refreshing...`, "success");

    // Wait 1 second then reload events
    setTimeout(() => {
      loadEvents();
    }, 1000);

  } catch (err) {
    showToast(`Simulation error: ${err.message}`, "error");
  }
}

// Helpers
function formatTime(isoStr) {
  if (!isoStr) return "N/A";
  try {
    const d = new Date(isoStr);
    return d.toLocaleString("th-TH", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit"
    });
  } catch {
    return isoStr.substring(0, 19).replace("T", " ");
  }
}

function renderLoading() {
  elements.timelineList.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Scanning Windows Event Log...</p>
    </div>
  `;
}

function renderError(msg) {
  elements.timelineList.innerHTML = `
    <div class="empty-state">
      <p style="font-size: 1.5rem; color: var(--color-crash)">⚠️</p>
      <p>${msg}</p>
    </div>
  `;
}

function renderEmptyDetail() {
  elements.detailContainer.innerHTML = `
    <div class="empty-state" style="height: 100%;">
      <p style="font-size: 2.5rem;">📋</p>
      <h3>No Event Selected</h3>
      <p>Select a crash or hang event from the timeline to inspect OS telemetry.</p>
    </div>
  `;
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function toggleRawJson() {
  const pre = document.getElementById("raw-json-pre");
  const arrow = document.getElementById("raw-toggle-arrow");
  if (pre.style.display === "none") {
    pre.style.display = "block";
    arrow.textContent = "▼";
  } else {
    pre.style.display = "none";
    arrow.textContent = "▶";
  }
}

function showToast(message, type = "info") {
  if (!elements.toastContainer) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
    <span>${message}</span>
  `;
  elements.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Start
document.addEventListener("DOMContentLoaded", initApp);
