/**
 * WinEvent Analyzer - Frontend Controller (v2.0)
 * Manages KPI metrics, multi-facet filtering, App Chips, tabbed inspection, and live simulation.
 */

const API_BASE = "";

// Application State
const state = {
  events: [],
  stats: null,
  selectedEvent: null,
  activeTab: "tab-overview",
  
  // Filters
  currentType: "ALL",
  currentCategory: "ALL",
  currentApp: null,
  currentHours: 48,
  currentSort: "time_desc",
  searchQuery: "",
  
  isLoading: false,
};

// DOM Elements
const elements = {
  sysHost: document.getElementById("sys-host"),
  sysEngine: document.getElementById("sys-engine"),
  
  // KPI Elements
  valTotal: document.getElementById("val-total"),
  valCrash: document.getElementById("val-crash"),
  valHang: document.getElementById("val-hang"),
  valTopApp: document.getElementById("val-top-app"),
  kpiTotal: document.getElementById("kpi-total"),
  kpiCrash: document.getElementById("kpi-crash"),
  kpiHang: document.getElementById("kpi-hang"),
  kpiTopApp: document.getElementById("kpi-top-app"),

  // Counts in tabs
  countAll: document.getElementById("count-all"),
  countCrash: document.getElementById("count-crash"),
  countHang: document.getElementById("count-hang"),

  // Controls & Filters
  typeButtons: document.querySelectorAll(".tab-btn"),
  categoryFilter: document.getElementById("category-filter"),
  timeFilter: document.getElementById("time-filter"),
  sortFilter: document.getElementById("sort-filter"),
  searchInput: document.getElementById("search-input"),
  btnClearFilters: document.getElementById("btn-clear-filters"),
  btnRefresh: document.getElementById("btn-refresh"),
  chipsList: document.getElementById("chips-list"),
  filterIndicator: document.getElementById("active-filter-indicator"),

  // Timeline & Detail
  timelineList: document.getElementById("timeline-list"),
  detailContent: document.getElementById("detail-content"),
  detailTabs: document.querySelectorAll(".detail-tab-btn"),

  // Simulation & Toast
  simButtons: document.querySelectorAll(".btn-sim"),
  toastContainer: document.getElementById("toast-container"),
};

// Application Bootstrap
async function initApp() {
  setupEventListeners();
  await loadSystemInfo();
  await refreshDashboard();
}

// Setup Event Listeners
function setupEventListeners() {
  // KPI Card clicks for instant filtering
  elements.kpiTotal.addEventListener("click", () => {
    resetFilters();
  });
  elements.kpiCrash.addEventListener("click", () => {
    setTypeFilter("CRASH");
  });
  elements.kpiHang.addEventListener("click", () => {
    setTypeFilter("HANG");
  });
  elements.kpiTopApp.addEventListener("click", () => {
    if (state.stats && state.stats.top_failing_app && state.stats.top_failing_app !== "None") {
      setAppFilter(state.stats.top_failing_app);
    }
  });

  // Type Filter Tabs
  elements.typeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      setTypeFilter(btn.dataset.type);
    });
  });

  // Category Filter
  elements.categoryFilter.addEventListener("change", (e) => {
    state.currentCategory = e.target.value;
    applyFilters();
  });

  // Time Window Filter
  elements.timeFilter.addEventListener("change", (e) => {
    state.currentHours = parseInt(e.target.value);
    refreshDashboard();
  });

  // Sort Order Filter
  elements.sortFilter.addEventListener("change", (e) => {
    state.currentSort = e.target.value;
    applyFilters();
  });

  // Live Search Input
  elements.searchInput.addEventListener("input", (e) => {
    state.searchQuery = e.target.value.toLowerCase().trim();
    applyFilters();
  });

  // Clear Filters Button
  elements.btnClearFilters.addEventListener("click", () => {
    resetFilters();
  });

  // Refresh Button
  elements.btnRefresh.addEventListener("click", () => {
    refreshDashboard();
  });

  // Simulation Buttons
  elements.simButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const simType = btn.dataset.sim;
      triggerSimulation(simType);
    });
  });

  // Detail Panel Tabs
  elements.detailTabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      elements.detailTabs.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeTab = btn.dataset.tab;
      renderDetailTab(state.selectedEvent);
    });
  });
}

// Fetch Host Environment Info
async function loadSystemInfo() {
  try {
    const res = await fetch(`${API_BASE}/api/system-info`);
    if (!res.ok) return;
    const info = await res.json();
    if (elements.sysHost) elements.sysHost.textContent = info.machine_name || "Windows PC";
    if (elements.sysEngine) elements.sysEngine.textContent = info.engine_mode || "PowerShell";
  } catch (err) {
    console.warn("Could not load system info:", err);
  }
}

// Refresh Entire Dashboard (Stats + Events)
async function refreshDashboard() {
  state.isLoading = true;
  renderLoading();

  try {
    // Parallel fetch stats and events
    const [statsRes, eventsRes] = await Promise.all([
      fetch(`${API_BASE}/api/stats?hours=${state.currentHours}`),
      fetch(`${API_BASE}/api/events?hours=${state.currentHours}&limit=300&type=ALL`)
    ]);

    if (statsRes.ok) {
      state.stats = await statsRes.json();
      renderStats(state.stats);
    }

    if (eventsRes.ok) {
      const data = await eventsRes.json();
      state.events = data.events || [];
      renderAppChips(state.events);
      applyFilters();
      showToast(`อัปเดตข้อมูลสำเร็จ (${state.events.length} เหตุการณ์)`, "info");
    }
  } catch (err) {
    renderError(`เกิดข้อผิดพลาดในการดึงข้อมูล: ${err.message}`);
    showToast("เชื่อมต่อ Event Log ไม่สำเร็จ", "error");
  } finally {
    state.isLoading = false;
  }
}

// Render KPI Cards
function renderStats(stats) {
  if (!stats) return;
  elements.valTotal.textContent = stats.total_events;
  elements.valCrash.textContent = stats.total_crashes;
  elements.valHang.textContent = stats.total_hangs;
  
  if (stats.top_failing_app && stats.top_failing_app !== "None") {
    elements.valTopApp.textContent = `${stats.top_failing_app} (${stats.top_failing_app_count})`;
  } else {
    elements.valTopApp.textContent = "ไม่มีประวัติ";
  }

  elements.countAll.textContent = stats.total_events;
  elements.countCrash.textContent = stats.total_crashes;
  elements.countHang.textContent = stats.total_hangs;
}

// Render App Chips
function renderAppChips(events) {
  const appCounts = {};
  events.forEach(e => {
    if (e.app_name) {
      appCounts[e.app_name] = (appCounts[e.app_name] || 0) + 1;
    }
  });

  const sortedApps = Object.entries(appCounts).sort((a, b) => b[1] - a[1]);

  let html = `
    <button type="button" class="app-chip ${!state.currentApp ? 'active' : ''}" data-app="">
      ทั้งหมด
    </button>
  `;

  sortedApps.slice(0, 8).forEach(([app, count]) => {
    const isActive = state.currentApp === app ? 'active' : '';
    html += `
      <button type="button" class="app-chip ${isActive}" data-app="${escapeHtml(app)}">
        ${escapeHtml(app)} <strong style="opacity: 0.7;">(${count})</strong>
      </button>
    `;
  });

  elements.chipsList.innerHTML = html;

  // Attach chip listeners
  elements.chipsList.querySelectorAll(".app-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      setAppFilter(chip.dataset.app || null);
    });
  });
}

// Filter Modifiers
function setTypeFilter(type) {
  state.currentType = type;
  elements.typeButtons.forEach(b => {
    b.classList.toggle("active", b.dataset.type === type);
  });
  applyFilters();
}

function setAppFilter(appName) {
  state.currentApp = appName;
  elements.chipsList.querySelectorAll(".app-chip").forEach(chip => {
    chip.classList.toggle("active", (chip.dataset.app || null) === appName);
  });
  applyFilters();
}

function resetFilters() {
  state.currentType = "ALL";
  state.currentCategory = "ALL";
  state.currentApp = null;
  state.searchQuery = "";
  elements.searchInput.value = "";
  elements.categoryFilter.value = "ALL";
  elements.typeButtons.forEach(b => b.classList.toggle("active", b.dataset.type === "ALL"));
  elements.chipsList.querySelectorAll(".app-chip").forEach(c => c.classList.toggle("active", !c.dataset.app));
  applyFilters();
  showToast("ล้างตัวกรองทั้งหมดแล้ว", "info");
}

// Apply Client-Side Filters and Sort
function applyFilters() {
  let filtered = state.events.filter((e) => {
    // 1. Type Filter
    if (state.currentType !== "ALL" && e.event_type !== state.currentType) {
      return false;
    }
    // 2. Category Filter
    if (state.currentCategory !== "ALL" && e.category !== state.currentCategory) {
      return false;
    }
    // 3. App Chip Filter
    if (state.currentApp && e.app_name !== state.currentApp) {
      return false;
    }
    // 4. Search Query (App, Module, Code, Symbol, Meaning, Category)
    if (state.searchQuery) {
      const q = state.searchQuery;
      const matchApp = (e.app_name || "").toLowerCase().includes(q);
      const matchMod = (e.module_name || "").toLowerCase().includes(q);
      const matchCode = (e.exception_code || "").toLowerCase().includes(q);
      const matchSymbol = (e.exception_symbol || "").toLowerCase().includes(q);
      const matchMeaning = (e.exception_meaning || "").toLowerCase().includes(q);
      const matchCat = (e.category_label || "").toLowerCase().includes(q);
      return matchApp || matchMod || matchCode || matchSymbol || matchMeaning || matchCat;
    }
    return true;
  });

  // Sorting
  if (state.currentSort === "time_asc") {
    filtered.sort((a, b) => (a.time_created || "").localeCompare(b.time_created || ""));
  } else if (state.currentSort === "app_asc") {
    filtered.sort((a, b) => (a.app_name || "").localeCompare(b.app_name || ""));
  } else {
    // time_desc
    filtered.sort((a, b) => (b.time_created || "").localeCompare(a.time_created || ""));
  }

  // Update Indicator
  const filterDesc = [];
  if (state.currentType !== "ALL") filterDesc.push(state.currentType);
  if (state.currentCategory !== "ALL") filterDesc.push(elements.categoryFilter.options[elements.categoryFilter.selectedIndex].text.split(' ')[1] || state.currentCategory);
  if (state.currentApp) filterDesc.push(`App: ${state.currentApp}`);
  if (state.searchQuery) filterDesc.push(`ค้นหา: "${state.searchQuery}"`);

  elements.filterIndicator.textContent = filterDesc.length > 0 ? filterDesc.join(" • ") : `แสดงทั้งหมด (${filtered.length})`;

  renderTimeline(filtered);

  // Manage Selected Event
  if (filtered.length > 0) {
    if (!state.selectedEvent || !filtered.some(e => e.record_id === state.selectedEvent.record_id)) {
      selectEvent(filtered[0]);
    } else {
      renderDetailTab(state.selectedEvent);
    }
  } else {
    state.selectedEvent = null;
    renderEmptyDetail();
  }
}

// Render Left Panel Timeline List
function renderTimeline(events) {
  if (events.length === 0) {
    elements.timelineList.innerHTML = `
      <div class="empty-state">
        <p style="font-size: 2rem;">🔍</p>
        <p style="font-weight: 600; color: #cbd5e1;">ไม่พบรายการเหตุการณ์ตามเงื่อนไขที่เลือก</p>
        <small style="color: var(--text-dim)">ลองเปลี่ยนช่วงเวลาหรือกดปุ่ม "ล้างตัวกรอง"</small>
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
      const icon = isCrash ? "💥" : "⏳";
      const codeOrHang = isCrash ? e.exception_code : (e.hang_type || "HANG");

      return `
        <div class="event-card ${cardTypeClass} ${isSelected ? 'active' : ''}" data-record-id="${e.record_id}">
          <div class="card-top">
            <div>
              <span class="badge ${badgeClass}">${icon} ${e.event_type} (${e.event_id})</span>
              <span class="category-tag">${escapeHtml(e.category_label || e.category)}</span>
            </div>
            <span class="card-time">${timeFormatted}</span>
          </div>

          <div class="card-app-name" title="${escapeHtml(e.app_name)}">
            ${escapeHtml(e.app_name)}
          </div>

          <div class="card-meta-row">
            <span class="card-code">${codeOrHang}</span>
            <span class="card-module" title="${escapeHtml(e.module_name || '')}">
              ${escapeHtml(e.module_name || 'N/A')}
            </span>
          </div>
        </div>
      `;
    })
    .join("");

  // Attach card click handlers
  elements.timelineList.querySelectorAll(".event-card").forEach((card, idx) => {
    card.addEventListener("click", () => {
      elements.timelineList.querySelectorAll(".event-card").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      selectEvent(events[idx]);
    });
  });
}

// Select Event
function selectEvent(event) {
  state.selectedEvent = event;
  renderDetailTab(event);
}

// Render Right Panel based on active tab
function renderDetailTab(e) {
  if (!e) {
    renderEmptyDetail();
    return;
  }

  const isCrash = e.event_type === "CRASH";
  const icon = isCrash ? "💥" : "⏳";
  const typeBadgeClass = isCrash ? "badge-crash" : "badge-hang";
  const timeFormatted = formatTime(e.time_created);
  const severityClass = `severity-${e.severity || 'MEDIUM'}`;

  // Common Header
  const headerHtml = `
    <div class="detail-header-card">
      <div>
        <div class="detail-app-heading">
          <span>${icon}</span>
          <span>${escapeHtml(e.app_name)}</span>
          <span class="badge ${typeBadgeClass}">${e.event_type} • ID ${e.event_id}</span>
          <span class="severity-pill ${severityClass}">ความรุนแรง: ${e.severity}</span>
        </div>
        <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.4rem;">
          บันทึกเมื่อ: <strong style="color: #cbd5e1;">${timeFormatted}</strong> • Record ID: <code>${e.record_id || 'N/A'}</code> • หมวดหมู่: <strong style="color: var(--accent-cyan);">${escapeHtml(e.category_label || e.category)}</strong>
        </div>
      </div>
    </div>
  `;

  // TAB 1: OVERVIEW & DIAGNOSIS
  if (state.activeTab === "tab-overview") {
    const checksHtml = (e.offline_checks && e.offline_checks.length > 0)
      ? e.offline_checks.map((chk, i) => `
          <label class="check-item">
            <input type="checkbox" id="chk-${i}">
            <span>${escapeHtml(chk)}</span>
          </label>
        `).join("")
      : `<p style="color: var(--text-dim); font-size: 0.85rem;">ไม่มีเช็กลิสต์แนะนำเฉพาะสำหรับรหัสนี้</p>`;

    elements.detailContent.innerHTML = `
      ${headerHtml}

      <!-- Tech to Human Diagnosis Box -->
      <div class="diag-card">
        <div class="diag-title">
          <span>📖</span> คำอธิบายอาการทางเทคนิค (Tech-to-Human Diagnosis)
        </div>
        <div class="diag-body">
          ${escapeHtml(e.exception_meaning || 'ไม่มีคำอธิบายออฟไลน์สำหรับรหัสนี้')}
        </div>
      </div>

      <!-- Actionable Checklist -->
      <div class="checklist-section">
        <div class="checklist-title">
          <span>✅</span> แนวทางการตรวจสอบและแก้ไขเบื้องต้น (Actionable Checks):
        </div>
        <div class="checklist-list">
          ${checksHtml}
        </div>
      </div>

      <!-- AI Readiness Box -->
      <div class="ai-teaser-box">
        <div class="ai-teaser-text">
          <strong>🤖 AI-Assisted Diagnosis Ready (Phase 3)</strong><br>
          ข้อมูลนี้พร้อมส่งเข้าสู่ Google Gemini Engine เพื่อวิเคราะห์หา Possible Causes และสร้างคำแนะนำเชิงลึก
        </div>
        <span class="badge" style="background: rgba(168, 85, 247, 0.25); color: #d8b4fe;">Phase 3 Prep</span>
      </div>
    `;
    return;
  }

  // TAB 2: DEEP OS TELEMETRY
  if (state.activeTab === "tab-telemetry") {
    elements.detailContent.innerHTML = `
      ${headerHtml}

      <div class="telemetry-grid">
        <div class="telemetry-item">
          <span class="telemetry-label">Exception Code / Status</span>
          <span class="telemetry-val" style="color: ${isCrash ? '#f87171' : '#fbbf24'}; font-weight: 700;">
            ${escapeHtml(e.exception_code)}
          </span>
        </div>

        <div class="telemetry-item">
          <span class="telemetry-label">Symbolic Name (Win32/NTSTATUS)</span>
          <span class="telemetry-val">${escapeHtml(e.exception_symbol || 'UNKNOWN')}</span>
        </div>

        <div class="telemetry-item">
          <span class="telemetry-label">Faulting Module (DLL/EXE)</span>
          <span class="telemetry-val">${escapeHtml(e.module_name || 'N/A')}</span>
        </div>

        <div class="telemetry-item">
          <span class="telemetry-label">Memory Fault Offset</span>
          <span class="telemetry-val">${escapeHtml(e.fault_offset || 'N/A')}</span>
        </div>

        <div class="telemetry-item">
          <span class="telemetry-label">Process ID (PID)</span>
          <span class="telemetry-val">${escapeHtml(e.process_id || 'N/A')}</span>
        </div>

        <div class="telemetry-item">
          <span class="telemetry-label">Application Version</span>
          <span class="telemetry-val">${escapeHtml(e.app_version || '0.0.0.0')}</span>
        </div>

        ${e.hang_type ? `
        <div class="telemetry-item" style="grid-column: 1 / -1;">
          <span class="telemetry-label">Hang Classification</span>
          <span class="telemetry-val" style="color: #fbbf24;">${escapeHtml(e.hang_type)}</span>
        </div>` : ''}

        <div class="telemetry-item path-box">
          <span class="telemetry-label">Application Path</span>
          <span class="telemetry-val">${escapeHtml(e.app_path || 'Unknown Path')}</span>
        </div>

        ${e.module_path ? `
        <div class="telemetry-item path-box">
          <span class="telemetry-label">Module File Path</span>
          <span class="telemetry-val">${escapeHtml(e.module_path)}</span>
        </div>` : ''}

        <div class="telemetry-item path-box">
          <span class="telemetry-label">Signature Hash (Cache Key)</span>
          <span class="telemetry-val" style="color: var(--accent-cyan);">
            ${e.signature_hash}
          </span>
        </div>
      </div>
    `;
    return;
  }

  // TAB 3: RAW JSON PAYLOAD
  if (state.activeTab === "tab-raw") {
    const jsonStr = JSON.stringify(e, null, 2);
    elements.detailContent.innerHTML = `
      ${headerHtml}

      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 0.85rem; color: var(--text-muted); font-weight: 600;">
          Normalized JSON Model (Pydantic v2 Schema):
        </span>
        <button type="button" class="btn-copy" id="btn-copy-json">
          <span>📋</span> คัดลอก JSON
        </button>
      </div>

      <pre class="raw-json-box">${escapeHtml(jsonStr)}</pre>
    `;

    document.getElementById("btn-copy-json")?.addEventListener("click", () => {
      navigator.clipboard.writeText(jsonStr);
      showToast("คัดลอก JSON สำเร็จแล้ว!", "success");
    });
  }
}

// Trigger Live Safe Simulation
async function triggerSimulation(simType) {
  showToast(`กำลังสั่งจำลองเหตุการณ์: [${simType}]...`, "info");

  try {
    const res = await fetch(`${API_BASE}/api/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ simulation_type: simType }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Simulation failed");

    showToast(`จำลองสำเร็จ! Windows บันทึก Event แล้ว กำลังรีเฟรช...`, "success");

    // Wait 1.2s then reload stats and events
    setTimeout(() => {
      refreshDashboard();
    }, 1200);

  } catch (err) {
    showToast(`จำลองล้มเหลว: ${err.message}`, "error");
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
      <p style="color: #cbd5e1; font-weight: 500;">กำลังดึงข้อมูลจาก Windows Event Log...</p>
    </div>
  `;
}

function renderError(msg) {
  elements.timelineList.innerHTML = `
    <div class="empty-state">
      <p style="font-size: 2rem; color: var(--color-crash)">⚠️</p>
      <p style="color: #f87171; font-weight: 600;">${msg}</p>
    </div>
  `;
}

function renderEmptyDetail() {
  elements.detailContent.innerHTML = `
    <div class="empty-state" style="height: 100%;">
      <p style="font-size: 3rem;">📋</p>
      <h3 style="color: #ffffff;">ยังไม่ได้เลือกเหตุการณ์</h3>
      <p style="max-width: 320px;">คลิกเลือกการ์ด Crash หรือ Hang จากรายการฝั่งซ้าย เพื่อดูข้อมูลเจาะลึกระดับ OS</p>
    </div>
  `;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
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

// Start Application
document.addEventListener("DOMContentLoaded", initApp);
