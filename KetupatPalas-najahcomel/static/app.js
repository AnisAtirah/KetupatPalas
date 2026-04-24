// ─── Dashboard Context: /api/context ─────────────────────────────────────────

async function loadContext() {
  try {
    const res  = await fetch('/api/context');
    const data = await res.json();

    document.getElementById('patientsValue').textContent = data.today_appointments + ' patients';
    document.getElementById('waitingTime').textContent   = data.current_wait + ' min';
    document.getElementById('staffNumber').textContent   = data.available_doctors + ' Dr / ' + data.available_nurses + ' RN';
    document.getElementById('bedValue').textContent      = data.available_beds + ' beds';

    // Apply zone colour to the hero bg-wrapper if element exists
    const wrapper = document.querySelector('.bg-wrapper');
    if (wrapper) {
      wrapper.classList.remove('green', 'yellow', 'red');
      if (data.zone === 'Red Zone')    wrapper.classList.add('red');
      else if (data.zone === 'Yellow Zone') wrapper.classList.add('yellow');
      else                             wrapper.classList.add('green');
    }
  } catch (err) {
    console.error('Context fetch failed:', err);
  }
}

// ─── AI Suggestions: /api/recommendations ────────────────────────────────────

let allSuggestions = [];

const priorityColor = { High: '#bd3535', Medium: '#b07d2e', Low: '#2a7d55' };

function renderSuggestions(suggestions) {
  const list = document.getElementById('suggestionList');
  if (!list) return;
  list.innerHTML = '';
  suggestions.slice(0, 3).forEach(s => {
    const card = document.createElement('div');
    card.className = 'suggestion-card';
    card.innerHTML = `
      <div style="font-weight:700; font-size:16px; margin-bottom:8px;">${s.title}</div>
      <div style="font-size:13px; color:var(--muted); margin-bottom:10px;">${s.explanation}</div>
      <span style="
        display:inline-block;
        background:${priorityColor[s.priority] || '#888'}22;
        color:${priorityColor[s.priority] || '#888'};
        border:1px solid ${priorityColor[s.priority] || '#888'};
        border-radius:20px;
        padding:2px 12px;
        font-size:12px;
        font-weight:700;
      ">${s.priority}</span>
    `;
    list.appendChild(card);
  });
}

function renderModal(suggestions) {
  const body = document.getElementById('modalBody');
  if (!body) return;
  body.innerHTML = '';
  suggestions.forEach((s, i) => {
    const card = document.createElement('div');
    card.className = 'info-card';
    card.innerHTML = `
      <h4>#${i + 1} — ${s.title}</h4>
      <p>${s.explanation}</p>
      <p style="margin-top:6px;"><strong>Priority:</strong>
        <span style="color:${priorityColor[s.priority] || '#888'}">${s.priority}</span>
      </p>
    `;
    body.appendChild(card);
  });
}

async function fetchRecommendations() {
  const list = document.getElementById('suggestionList');
  if (!list) return;
  list.innerHTML = '<div class="suggestion-card">Generating recommendations…</div>';
  try {
    const res  = await fetch('/api/recommendations');
    const data = await res.json();
    allSuggestions = data.suggestions || [];
    renderSuggestions(allSuggestions);
  } catch (err) {
    console.error('Recommendations fetch failed:', err);
    if (list) list.innerHTML = '<div class="suggestion-card">Failed to load recommendations.</div>';
  }
}

// Generate button
const generateBtn = document.getElementById('generateBtn');
if (generateBtn) generateBtn.addEventListener('click', fetchRecommendations);

// See All modal
const seeAllBtn    = document.getElementById('seeAllBtn');
const modal        = document.getElementById('modal');
const closeModalBtn = document.getElementById('closeModalBtn');

if (seeAllBtn) {
  seeAllBtn.addEventListener('click', () => {
    renderModal(allSuggestions);
    if (modal) modal.classList.remove('hidden');
  });
}
if (closeModalBtn) {
  closeModalBtn.addEventListener('click', () => {
    if (modal) modal.classList.add('hidden');
  });
}
if (modal) {
  modal.addEventListener('click', e => {
    if (e.target === modal) modal.classList.add('hidden');
  });
}

// ─── Simulation: /api/simulate ───────────────────────────────────────────────

let simTick = 0;

function badge(value, unit = '') {
  const isUp  = value > 0;
  const sign  = isUp ? '+' : '';
  const color = isUp ? '#e05c5c' : '#4caf82';
  const bg    = isUp ? 'rgba(224,92,92,0.12)' : 'rgba(76,175,130,0.12)';
  return `<span style="
    display:inline-block;
    background:${bg};
    color:${color};
    border:1px solid ${color};
    border-radius:6px;
    padding:2px 10px;
    font-size:15px;
    font-weight:700;
    font-family:'Lexend Deca',sans-serif;
  ">${sign}${value.toFixed(1)}${unit}</span>`;
}

function addSimLog(data) {
  const log = document.getElementById('simLog');
  if (!log) return;
  const entry = document.createElement('div');
  entry.style.cssText = `
    font-size:12px;
    font-family:'Lexend Deca',sans-serif;
    padding:5px 10px;
    border-left:3px solid var(--grey-azure, #888);
    background:rgba(255,255,255,0.03);
    border-radius:0 4px 4px 0;
    color:var(--grey-azure);
  `;
  entry.innerHTML = `
    <span style="opacity:0.45">tick ${simTick}&nbsp;&nbsp;</span>
    ${badge(data.cost_change, ' RM')}&nbsp;
    ${badge(data.waiting_time_change, ' min')}&nbsp;
    <span style="opacity:0.75">${data.interpretation}</span>
  `;
  log.insertBefore(entry, log.firstChild);
  while (log.children.length > 20) log.removeChild(log.lastChild);
}

function updateSimUI(data) {
  simTick++;
  const el = id => document.getElementById(id);

  if (el('simCostChange')) el('simCostChange').innerHTML = badge(data.cost_change, ' RM');
  if (el('simWaitChange')) el('simWaitChange').innerHTML = badge(data.waiting_time_change, ' min');

  if (el('simDoctors')) el('simDoctors').textContent = data.state.doctors;
  if (el('simNurses'))  el('simNurses').textContent  = data.state.nurses;
  if (el('simIcu'))     el('simIcu').textContent     = data.state.icu_patients;
  if (el('simWard'))    el('simWard').textContent    = data.state.ward_patients;
  if (el('simEr'))      el('simEr').textContent      = data.state.er_patients;

  if (el('simInterpretation')) el('simInterpretation').textContent = data.interpretation;
  if (el('simInsight'))        el('simInsight').textContent        = data.insight;

  addSimLog(data);
}

async function fetchSimulate() {
  try {
    const res  = await fetch('/api/simulate');
    const data = await res.json();
    updateSimUI(data);
  } catch (err) {
    console.error('Simulation fetch failed:', err);
  }
}

// ─── Boot ─────────────────────────────────────────────────────────────────────

loadContext();           // populate hero cards immediately
fetchRecommendations();  // load AI suggestions on page load
fetchSimulate();         // start simulation
setInterval(fetchSimulate, 10000);