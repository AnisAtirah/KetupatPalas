# Smart Hospital Resources Management Prototype

A simple full-stack prototype for your project. It uses your uploaded CSV files to create a small hospital dashboard with:

- baseline demand summary from dataset
- what-if simulation for patients, doctors, nurses, and beds
- recommendation endpoint
- z.ai-ready backend integration

## Project structure

- `backend/app.py` - Flask backend and API routes
- `backend/process_data.py` - builds processed datasets from your raw CSVs
- `backend/requirements.txt` - Python packages
- `frontend/index.html` - UI
- `frontend/styles.css` - styling
- `frontend/script.js` - frontend logic
- `data/raw/` - your original CSV files
- `data/processed/` - derived summary datasets

## API routes

- `GET /api/summary`
- `POST /api/simulate`
- `POST /api/recommendation`

## Run locally

```bash
cd smart_hospital_app/backend
python -m pip install -r requirements.txt
python process_data.py
python app.py
```

Then open:

```bash
http://127.0.0.1:5000
```

## z.ai integration

The app already works without z.ai. It falls back to rule-based recommendations.

When you get the API key, set these environment variables:

```bash
export ZAI_API_KEY=your_key_here
export ZAI_MODEL=glm-5.1
# optional
export ZAI_BASE_URL=https://api.z.ai/api/paas/v4
```

For Windows PowerShell:

```powershell
$env:ZAI_API_KEY="your_key_here"
$env:ZAI_MODEL="glm-5.1"
$env:ZAI_BASE_URL="https://api.z.ai/api/paas/v4"
```

The backend calls Z.AI's chat completions endpoint using the general base URL and bearer auth, which is documented in Z.AI's official docs. citeturn101818view1turn101818view0

## Dataset note

Your current dataset supports:

- doctor workload
- appointment demand
- specialization demand
- rough cost view from billing
- procedure complexity proxy

It does not directly contain nurses, beds, stock, or real waiting times, so those are handled as user inputs in the simulator.

## Suggested next step tomorrow

Replace the rule-based explanation with z.ai output, then add one chart and one scenario comparison table.


## New comparison feature
- Baseline vs Potential table after each simulation
- Recent Scenario History to compare past runs
- Saved history is stored in `data/processed/simulation_history.json`
