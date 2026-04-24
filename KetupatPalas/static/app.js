// ─── Page detection ───────────────────────────────────────────────────────────

const ON_DASHBOARD = !!document.getElementById("patientsValue");
const ON_SIMULATOR = !!document.getElementById("simForm");


// =============================================================================
// DASHBOARD
// =============================================================================

if (ON_DASHBOARD) {

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function setHtml(id, html) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  }

  function colorVal(val) {
    if (val == null) return "--";
    const sign  = val > 0 ? "+" : "";
    const color = val > 0 ? "#c0392b" : "#1a7a5e";
    return `<span style="color:${color};font-weight:700;">${sign}${val}</span>`;
  }

  // ── CONTEXT (TOP CARDS) ─────────────────────────────────────────────────────

  async function loadContext() {
    try {
      const res = await fetch("/api/context");
      const d = await res.json();

      setText("patientsValue", d.today_appointments + " patients");
      setText("waitingTime",   d.current_wait + " min");
      setText("staffDoctors",  d.available_doctors + " Doctors");
      setText("staffNurses",   d.available_nurses + " Nurses");
      setText("bedValue",      d.available_beds + " beds");

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

  // ── AI RECOMMENDATIONS ──────────────────────────────────────────────────────

  function suggestionHTML(s) {
    const priority = (s.priority || "").toLowerCase();
    return `
      <div class="suggestion-card">
        <div style="font-weight:700; margin-bottom:6px;">
          <span class="priority-badge priority-${priority}">${s.priority || ""}</span>
          ${s.title}
        </div>
        <div style="font-size:13px; color:#777;">${s.explanation}</div>
      </div>`;
  }

  async function loadRecommendations() {
    try {
      const res = await fetch("/api/recommendations");
      const d = await res.json();
      const suggestions = d.suggestions || [];
      setHtml("suggestionList", suggestions.map(suggestionHTML).join(""));
    } catch (e) {
      console.error("loadRecommendations failed:", e);
      setHtml("suggestionList", `<div class="suggestion-card">Failed to load.</div>`);
    }
  }

  // ── SIMULATION (RIGHT PANEL) ────────────────────────────────────────────────

  async function tickSimulation() {
    try {
      const res = await fetch("/api/simulate-dashboard");
      const d = await res.json();
      const s = d.state || {};

      setHtml("simCostChange", colorVal(Math.round(d.cost_change)));
      setHtml("simWaitChange", colorVal(Math.round(d.waiting_time_change * 10) / 10));

      setText("simDoctors", s.doctors);
      setText("simNurses", s.nurses);
      setText("simInterpretation", d.interpretation);
      setText("simInsight", d.insight);

    } catch (e) {
      console.error("tickSimulation failed:", e);
    }
  }

  // ── FIX: SYNC BOTH DATA ─────────────────────────────────────────────────────

  async function refreshDashboard() {
    await tickSimulation();   // FIRST → generate data
    await loadContext();      // THEN → use same data
  }

  // ── BUTTON ──────────────────────────────────────────────────────────────────

  const generateBtn = document.getElementById("generateBtn");
  if (generateBtn) {
    generateBtn.addEventListener("click", async () => {
      generateBtn.textContent = "Generating...";
      await loadRecommendations();
      generateBtn.textContent = "Generate +";
    });
  }

  // ── BOOT ────────────────────────────────────────────────────────────────────

  loadRecommendations();
  refreshDashboard();

  // 🔥 5 MINUTES UPDATE (IMPORTANT)
  setInterval(refreshDashboard, 300000);
}


// =============================================================================
// SIMULATOR PAGE
// =============================================================================

if (ON_SIMULATOR) {

  const form               = document.getElementById("simForm");
  const resultCards        = document.getElementById("resultCards");
  const recommendationText = document.getElementById("recommendationText");

  function card(title, value) {
    return `<div class="metric-card"><p>${title}</p><strong>${value}</strong></div>`;
  }

  async function runSimulation(payload) {
    resultCards.innerHTML = card("Status", "Running...");
    recommendationText.textContent = "Loading...";

    try {
      const simRes = await fetch("/api/simulate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });

      const { results: r } = await simRes.json();

      resultCards.innerHTML = [
        card("Wait Time", r.estimated_wait_time_minutes + " min"),
        card("Patients Served", r.estimated_patients_served),
        card("Doctor Load", r.doctor_load),
        card("Nurse Load", r.nurse_load),
        card("Cost", "RM " + r.staffing_cost_rm),
        card("Status", r.status),
      ].join("");

      const recRes = await fetch("/api/recommendation", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });

      const recData = await recRes.json();
      recommendationText.textContent = recData.recommendation;

    } catch (e) {
      console.error("Simulation failed:", e);
      resultCards.innerHTML = card("Error", "Failed");
      recommendationText.textContent = "Error loading recommendation.";
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    const payload = {
      add_doctors: Number(document.getElementById("add_doctors").value),
      add_nurses: Number(document.getElementById("add_nurses").value),
      add_beds: Number(document.getElementById("add_beds").value),
    };

    runSimulation(payload);
  });
}