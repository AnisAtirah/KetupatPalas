const suggestionList = document.getElementById('suggestionList');
const generateBtn = document.getElementById('generateBtn');
const seeAllBtn = document.getElementById('seeAllBtn');
const statusBox = document.getElementById('statusBox');
const modal = document.getElementById('modal');
const modalBody = document.getElementById('modalBody');
const closeModalBtn = document.getElementById('closeModalBtn');

let latestSuggestions = [];

function createSuggestionCard(item) {
  return `
    <article class="suggestion-item">
      <div class="suggestion-title">${item.title}</div>
      <div class="suggestion-explanation">${item.explanation}</div>
    </article>
  `;
}

function renderSuggestions(items) {
  suggestionList.innerHTML = items.slice(0, 3).map(createSuggestionCard).join('');
}

function renderModal(items) {
  modalBody.innerHTML = items.map(item => `
    <div class="detail-card">
      <div class="suggestion-title">${item.title}</div>
      <div class="suggestion-explanation">${item.explanation}</div>
      <span class="badge">Priority: ${item.priority || 'N/A'}</span>
    </div>
  `).join('');
}

async function loadContext() {
  try {
    const res = await fetch('/api/context');
    const data = await res.json();
    statusBox.textContent = `${data.zone} • ${data.status} • Wait ${data.current_wait} min`;
  } catch (error) {
    statusBox.textContent = 'Unable to load system status';
  }
}

async function generateSuggestions() {
  generateBtn.disabled = true;
  generateBtn.textContent = 'Generating...';

  suggestionList.innerHTML = `
    <div class="suggestion-item skeleton"></div>
    <div class="suggestion-item skeleton"></div>
    <div class="suggestion-item skeleton"></div>
  `;

  try {
    const res = await fetch('/api/recommendations');
    const data = await res.json();
    latestSuggestions = data.suggestions || [];
    renderSuggestions(latestSuggestions);

    const sourceText = data.source === 'ilmu-api' ? 'AI-powered suggestions loaded' : 'Fallback suggestions loaded';
    statusBox.textContent = `${sourceText}`;
  } catch (error) {
    statusBox.textContent = 'Failed to generate suggestions';
    suggestionList.innerHTML = `
      <article class="suggestion-item">
        <div class="suggestion-title">Error</div>
        <div class="suggestion-explanation">Please make sure the Flask backend is running on port 5000.</div>
      </article>
    `;
  } finally {
    generateBtn.disabled = false;
    generateBtn.textContent = 'Generate ✦';
  }
}

generateBtn.addEventListener('click', generateSuggestions);
seeAllBtn.addEventListener('click', () => {
  if (!latestSuggestions.length) return;
  renderModal(latestSuggestions);
  modal.classList.remove('hidden');
});
closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));
modal.addEventListener('click', (event) => {
  if (event.target === modal) {
    modal.classList.add('hidden');
  }
});

loadContext();
generateSuggestions();
