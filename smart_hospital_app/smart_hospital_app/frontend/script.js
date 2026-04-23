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

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function formatRecommendation(text) {
  if (!text) {
    return `<p>No recommendation available.</p>`;
  }

  const safeText = escapeHtml(text);

  const matches = [...safeText.matchAll(/\*\*(.+?):\*\*\s*([\s\S]*?)(?=\s*\*\*.+?:\*\*|$)/g)];

  if (matches.length === 0) {
    return `<p>${safeText.replace(/\n/g, "<br>")}</p>`;
  }

  return matches
    .map((match) => {
      const title = match[1].trim();
      const content = match[2].trim().replace(/\n/g, "<br>");

      return `
        <div class="ai-block">
          <h4>${title}</h4>
          <p>${content}</p>
        </div>
      `;
    })
    .join("");
}

async function loadSummary() {
  try {
    const res = await fetch("/api/summary");
    const data = await res.json();

    const real = data.real_inputs || {};

    document.getElementById("patients").value = real.patients ?? "";
    document.getElementById("doctors").value = real.doctors ?? "";
    document.getElementById("nurses").value = real.nurses ?? "";
    document.getElementById("beds").value = real.beds ?? "";
    document.getElementById("avg_complexity").value = 2;
  } catch (error) {
    console.error("Summary load error:", error);
  }
}

function renderResults(simData) {
  const r = simData.results;

  resultCards.innerHTML = `
    ${card("Wait Time", `${r.wait_time} min`)}
    ${card("Patients Served", r.patients_served)}
    ${card("Doctor Load", r.doctor_load)}
    ${card("Nurse Load", r.nurse_load)}
    ${card("Estimated Bed Need", r.estimated_bed_need)}
    ${card("Added Cost", `RM${r.cost}`)}
    ${card("Status", r.status)}
  `;
}

async function runSimulation(payload) {
  try {
    const simRes = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const simData = await simRes.json();
    renderResults(simData);

    const recRes = await fetch("/api/recommendation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const recData = await recRes.json();
    recommendationText.innerHTML = formatRecommendation(recData.recommendation);
  } catch (error) {
    console.error("Simulation error:", error);
    recommendationText.innerHTML = `<p>Unable to load recommendation right now.</p>`;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const payload = {
    add_doctors: Number(document.getElementById("add_doctors").value),
    add_nurses: Number(document.getElementById("add_nurses").value),
    add_beds: Number(document.getElementById("add_beds").value),
  };

  recommendationText.innerHTML = `<p>Loading recommendation...</p>`;
  await runSimulation(payload);
});

loadSummary();