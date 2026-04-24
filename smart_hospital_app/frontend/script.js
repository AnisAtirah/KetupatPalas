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

async function loadSummary() {
  const res = await fetch("/api/summary");
  const data = await res.json();
  const baseline = data.baseline;

  document.getElementById("patients").value = baseline.patients;
  document.getElementById("doctors").value = baseline.doctors;
  document.getElementById("nurses").value = baseline.nurses;
  document.getElementById("beds").value = baseline.beds;
  document.getElementById("avg_complexity").value = baseline.avg_complexity;
}

async function runSimulation(payload) {
  const simRes = await fetch("/api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const simData = await simRes.json();
  const r = simData.results;

  resultCards.innerHTML = `
    ${card("Wait Time", r.estimated_wait_time_minutes + " min")}
    ${card("Patients Served", r.estimated_patients_served)}
    ${card("Doctor Load", r.doctor_load)}
    ${card("Nurse Load", r.nurse_load)}
    ${card("Added Cost", "RM" + r.staffing_cost_rm)}
    ${card("Status", r.status)}
  `;

  const recRes = await fetch("/api/recommendation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const recData = await recRes.json();
  recommendationText.textContent = recData.recommendation;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const payload = {
    add_doctors: Number(document.getElementById("add_doctors").value),
    add_nurses: Number(document.getElementById("add_nurses").value),
    add_beds: Number(document.getElementById("add_beds").value),
  };

  recommendationText.textContent = "Loading recommendation...";
  await runSimulation(payload);
});

loadSummary();