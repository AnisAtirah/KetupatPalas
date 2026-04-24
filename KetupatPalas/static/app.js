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
    if (val == null || Number.isNaN(val)) return "--";

    const sign = val > 0 ? "+" : "";
    const color = val > 0 ? "#c0392b" : "#1a7a5e";

    return `<span style="color:${color};font-weight:700;">${sign}${val}</span>`;
  }


  // ── TOP SITUATION CARDS ─────────────────────────────────────────────────────

  async function loadContext() {
    try {
      const res = await fetch("/api/context");
      if (!res.ok) throw new Error(res.status);

      const d = await res.json();

      setText("patientsValue", d.today_appointments + " patients");
      setText("waitingTime", d.current_wait + " min");
      setText("staffDoctors", d.available_doctors + " Doctors");
      setText("staffNurses", d.available_nurses + " Nurses");
      setText("bedValue", d.available_beds + " beds");

      const wrapper = document.querySelector(".bg-wrapper");

      if (wrapper && d.zone) {
        wrapper.classList.remove("green", "yellow", "red");

        if (d.zone === "Red Zone") {
          wrapper.classList.add("red");
        } else if (d.zone === "Yellow Zone") {
          wrapper.classList.add("yellow");
        } else {
          wrapper.classList.add("green");
        }
      }

    } catch (e) {
      console.error("loadContext failed:", e);
    }
  }


  // ── AI SUGGESTION CARDS ─────────────────────────────────────────────────────

  function suggestionHTML(s) {
    const priority = (s.priority || "").toLowerCase();

    return `
      <div class="suggestion-card">
        <div style="font-weight:700; margin-bottom:6px;">
          <span class="priority-badge priority-${priority}">
            ${s.priority || ""}
          </span>
          ${s.title || "Recommendation"}
        </div>
        <div style="font-size:13px; color:var(--grey-brown, #777);">
          ${s.explanation || ""}
        </div>
      </div>
    `;
  }

  async function loadRecommendations() {
    try {
      const res = await fetch("/api/recommendations");
      if (!res.ok) throw new Error(res.status);

      const d = await res.json();
      const suggestions = d.suggestions || [];

      if (suggestions.length === 0) {
        setHtml("suggestionList", `<div class="suggestion-card">No recommendation available.</div>`);
        return;
      }

      setHtml("suggestionList", suggestions.map(suggestionHTML).join(""));

    } catch (e) {
      console.error("loadRecommendations failed:", e);

      setHtml(
        "suggestionList",
        `<div class="suggestion-card">Could not load recommendations.</div>`
      );
    }
  }


  // ── COST VS EFFICIENCY LIVE SIMULATION ──────────────────────────────────────

  async function tickSimulation() {
    try {
      const res = await fetch("/api/simulate-dashboard");
      if (!res.ok) throw new Error(res.status);

      const d = await res.json();
      const s = d.state || {};

      setHtml("simCostChange", colorVal(Math.round(d.cost_change)));
      setHtml(
        "simWaitChange",
        colorVal(Math.round(d.waiting_time_change * 10) / 10)
      );

      setText("simDoctors", s.doctors ?? "--");
      setText("simNurses", s.nurses ?? "--");

      setText("simIcu", s.icu_patients ?? "--");
      setText("simWard", s.ward_patients ?? "--");
      setText("simEr", s.er_patients ?? "--");

      setText("simInterpretation", d.interpretation ?? "--");
      setText("simInsight", d.insight ?? "--");

    } catch (e) {
      console.error("tickSimulation failed:", e);
    }
  }


  // ── KEEP TOP CARDS AND CURRENT STATE SAME ───────────────────────────────────

  async function refreshDashboard() {
    await tickSimulation();
    await loadContext();
  }


  // ── GENERATE BUTTON ─────────────────────────────────────────────────────────

  const generateBtn = document.getElementById("generateBtn");

  if (generateBtn) {
    generateBtn.addEventListener("click", async () => {
      generateBtn.disabled = true;
      generateBtn.textContent = "Generating...";

      setHtml("suggestionList", `
        <div class="suggestion-card">Loading...</div>
        <div class="suggestion-card">Loading...</div>
        <div class="suggestion-card">Loading...</div>
      `);

      await loadRecommendations();

      generateBtn.disabled = false;
      generateBtn.textContent = "Generate +";
    });
  }


  // ── BOOT DASHBOARD ──────────────────────────────────────────────────────────

  loadRecommendations();
  refreshDashboard();

  // 5 minutes = 300000 ms
  setInterval(refreshDashboard, 300000);
}



// =============================================================================
// SIMULATOR PAGE
// =============================================================================

if (ON_SIMULATOR) {

  const form = document.getElementById("simForm");
  const resultCards = document.getElementById("resultCards");
  const recommendationText = document.getElementById("recommendationText");

  function card(title, value) {
    return `
      <div class="metric-card">
        <p class="muted">${title}</p>
        <strong>${value}</strong>
      </div>
    `;
  }

  function cleanNumber(value) {
    const num = Number(value);
    return Number.isFinite(num) && num >= 0 ? num : 0;
  }

  function renderAnalysisBox(data) {
    recommendationText.innerHTML = `
      <div style="margin-bottom:14px;">
        <strong>Performance Analysis:</strong><br>
        <span>${data.analysis || "No analysis available."}</span>
      </div>

      <div style="margin-bottom:14px;">
        <strong>Recommendation:</strong><br>
        <span>${data.recommendation || "No recommendation available."}</span>
      </div>

      <div>
        <strong>Cost Impact:</strong><br>
        <span>${data.cost_impact || "No cost impact available."}</span>
      </div>
    `;
  }

  async function runSimulation(payload) {
    resultCards.innerHTML = card("Status", "Running...");
    recommendationText.textContent = "Loading recommendation...";

    try {
      const simRes = await fetch("/api/simulate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload),
      });

      if (!simRes.ok) {
        throw new Error(`Simulation HTTP ${simRes.status}`);
      }

      const simData = await simRes.json();
      const r = simData.results;

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
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload),
      });

      if (!recRes.ok) {
        throw new Error(`Recommendation HTTP ${recRes.status}`);
      }

      const recData = await recRes.json();
      renderAnalysisBox(recData);

    } catch (e) {
      console.error("Simulation failed:", e);

      resultCards.innerHTML = card("Error", "Failed");
      recommendationText.textContent =
        "Could not fetch recommendation. Please check the backend server.";
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    const payload = {
      add_doctors: cleanNumber(document.getElementById("add_doctors").value),
      add_nurses: cleanNumber(document.getElementById("add_nurses").value),
      add_beds: cleanNumber(document.getElementById("add_beds").value),
    };

    runSimulation(payload);
  });
}