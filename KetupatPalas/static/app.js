// ─── Page detection ───────────────────────────────────────────────────────────
// Each page has unique element IDs. We use these to scope logic safely.

const ON_DASHBOARD = !!document.getElementById("patientsValue");
const ON_SIMULATOR = !!document.getElementById("simForm");


// =============================================================================
// DASHBOARD  (index.html)
// =============================================================================

if (ON_DASHBOARD) {

  // ── Tiny helpers ────────────────────────────────────────────────────────────

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  // ── Coloured delta badge ─────────────────────────────────────────────────────

  function colorVal(val) {
    if (val == null) return "--";
    const sign  = val > 0 ? "+" : "";
    const color = val > 0 ? "#c0392b" : "#1a7a5e";
    return `<span style="color:${color};font-weight:700;">${sign}${val}</span>`;
  }

  // ── /api/context  →  hero stat cards ────────────────────────────────────────

  async function loadContext() {
    try {
      const res = await fetch("/api/context");
      if (!res.ok) throw new Error(res.status);
      const d = await res.json();

      setText("patientsValue", d.today_appointments != null ? d.today_appointments + " patients" : "--");
      setText("waitingTime",   d.current_wait       != null ? d.current_wait + " min"            : "--");
      setText("staffDoctors",  d.available_doctors != null ? d.available_doctors + " Doctors" : "--");
      setText("staffNurses",   d.available_nurses  != null ? d.available_nurses  + " Nurses"  : "--");
      setText("bedValue",      d.available_beds     != null ? d.available_beds + " beds"         : "--");

      // Zone colour on hero bg
      const wrapper = document.querySelector('.bg-wrapper');
      if (wrapper && d.zone) {
        wrapper.classList.remove('green', 'yellow', 'red');
        if      (d.zone === 'Red Zone')    wrapper.classList.add('red');
        else if (d.zone === 'Yellow Zone') wrapper.classList.add('yellow');
        else                               wrapper.classList.add('green');
      }
    } catch (e) {
      console.error("loadContext failed:", e);
    }
  }

  // ── /api/recommendations  →  AI suggestion cards ────────────────────────────

  function suggestionHTML(s) {
    const priority = (s.priority || "").toLowerCase();
    return `
      <div class="suggestion-card">
        <div style="font-weight:700; margin-bottom:6px;">
          <span class="priority-badge priority-${priority}">${s.priority || ""}</span>
          ${s.title}
        </div>
        <div style="font-size:13px; color:var(--grey-brown, #888);">${s.explanation}</div>
      </div>`;
  }

  async function loadRecommendations() {
    try {
      const res = await fetch("/api/recommendations");
      if (!res.ok) throw new Error(res.status);
      const d = await res.json();
      const suggestions = d.suggestions || [];
      setHtml("suggestionList", suggestions.map(suggestionHTML).join(""));
      return suggestions;
    } catch (e) {
      console.error("loadRecommendations failed:", e);
      setHtml("suggestionList", `<div class="suggestion-card">Could not load suggestions.</div>`);
      return [];
    }
  }

  // ── /api/simulate-dashboard  →  Cost vs Efficiency live ticker ──────────────

  function addLog(msg) {
    const log = document.getElementById("simLog");
    if (!log) return;
    const row = document.createElement("div");
    row.style.cssText = "font-size:11px; color:var(--grey-azure,#888); padding:3px 6px; border-left:3px solid var(--grey-azure,#ccc); background:rgba(255,255,255,0.25); border-radius:0 4px 4px 0;";
    row.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    log.prepend(row);
    while (log.children.length > 20) log.removeChild(log.lastChild);
  }

  async function tickSimulation() {
    try {
      const res = await fetch("/api/simulate-dashboard");
      if (!res.ok) throw new Error(res.status);
      const d = await res.json();
      const s = d.state || {};

      setHtml("simCostChange",  colorVal(d.cost_change         != null ? Math.round(d.cost_change)                    : null));
      setHtml("simWaitChange",  colorVal(d.waiting_time_change != null ? Math.round(d.waiting_time_change * 10) / 10  : null));

      setText("simDoctors",        s.doctors       ?? "--");
      setText("simNurses",         s.nurses        ?? "--");
      setText("simIcu",            s.icu_patients  ?? "--");
      setText("simWard",           s.ward_patients ?? "--");
      setText("simEr",             s.er_patients   ?? "--");
      setText("simInterpretation", d.interpretation ?? "--");
      setText("simInsight",        d.insight        ?? "--");

      addLog(d.interpretation || "tick");
    } catch (e) {
      console.error("tickSimulation failed:", e);
      addLog("Update failed — retrying next tick.");
    }
  }

  // ── Generate button ──────────────────────────────────────────────────────────

  const generateBtn = document.getElementById("generateBtn");
  if (generateBtn) {
    generateBtn.addEventListener("click", async () => {
      generateBtn.disabled    = true;
      generateBtn.textContent = "Generating…";
      setHtml("suggestionList", `
        <div class="suggestion-card">Loading...</div>
        <div class="suggestion-card">Loading...</div>
        <div class="suggestion-card">Loading...</div>`);
      await loadRecommendations();
      generateBtn.disabled    = false;
      generateBtn.textContent = "Generate +";
    });
  }

  // ── See All modal ────────────────────────────────────────────────────────────

  const modal      = document.getElementById("modal");
  const modalBody  = document.getElementById("modalBody");
  const seeAllBtn  = document.getElementById("seeAllBtn");
  const closeBtn   = document.getElementById("closeModalBtn");

  if (seeAllBtn && modal) {
    seeAllBtn.addEventListener("click", async () => {
      modal.classList.remove("hidden");
      try {
        const res = await fetch("/api/recommendations");
        const d   = await res.json();
        if (modalBody) {
          // Use info-card style inside the modal for a richer look
          modalBody.innerHTML = (d.suggestions || []).map((s, i) => {
            const priority = (s.priority || "").toLowerCase();
            return `
              <div class="info-card">
                <h4>#${i + 1} — ${s.title}
                  <span class="priority-badge priority-${priority}" style="margin-left:8px;">${s.priority || ""}</span>
                </h4>
                <p>${s.explanation}</p>
              </div>`;
          }).join("");
        }
      } catch {
        if (modalBody) modalBody.innerHTML = "<p>Could not load recommendations.</p>";
      }
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
    modal.addEventListener("click", e => { if (e.target === modal) modal.classList.add("hidden"); });
  }

  // ── Boot ─────────────────────────────────────────────────────────────────────

  loadContext();
  loadRecommendations();
  tickSimulation();
  setInterval(tickSimulation, 10000);
}


// =============================================================================
// SIMULATOR  (simulator.html)
// =============================================================================

if (ON_SIMULATOR) {

  const form               = document.getElementById("simForm");
  const resultCards        = document.getElementById("resultCards");
  const recommendationText = document.getElementById("recommendationText");

  function card(title, value) {
    return `<div class="metric-card"><p class="muted">${title}</p><strong>${value}</strong></div>`;
  }

  function setField(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    if (["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName)) el.value = value;
    else el.textContent = value;
  }

  // Pre-fill baseline values from real CSV data
  async function loadSummary() {
    try {
      const res = await fetch("/api/summary");
      if (!res.ok) throw new Error(res.status);
      const { baseline } = await res.json();
      setField("patients",       baseline.patients);
      setField("doctors",        baseline.doctors);
      setField("nurses",         baseline.nurses);
      setField("beds",           baseline.beds);
      setField("avg_complexity", baseline.avg_complexity);
    } catch (e) {
      console.error("loadSummary failed:", e);
    }
  }

  async function runSimulation(payload) {
    resultCards.innerHTML          = card("Status", "Running…");
    recommendationText.textContent = "Loading recommendation…";

    try {
      // Simulation results
      const simRes = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!simRes.ok) throw new Error(`Simulate HTTP ${simRes.status}`);
      const { results: r } = await simRes.json();

      resultCards.innerHTML = [
        card("Wait Time",       r.estimated_wait_time_minutes + " min"),
        card("Patients Served", r.estimated_patients_served),
        card("Doctor Load",     r.doctor_load),
        card("Nurse Load",      r.nurse_load),
        card("Added Cost",      "RM " + r.staffing_cost_rm),
        card("Status",          r.status),
      ].join("");

      // AI recommendation
      const recRes = await fetch("/api/recommendation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!recRes.ok) throw new Error(`Recommendation HTTP ${recRes.status}`);
      const recData = await recRes.json();
      recommendationText.textContent = recData.recommendation;

    } catch (e) {
      console.error("runSimulation failed:", e);
      resultCards.innerHTML          = card("Error", "Request failed");
      recommendationText.textContent = "Could not fetch recommendation. Check the server.";
    }
  }

  form.addEventListener("submit", async e => {
    e.preventDefault();
    await runSimulation({
      add_doctors: Number(document.getElementById("add_doctors").value),
      add_nurses:  Number(document.getElementById("add_nurses").value),
      add_beds:    Number(document.getElementById("add_beds").value),
    });
  });

  loadSummary();
}