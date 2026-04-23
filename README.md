# Smart Hospital Resources Management

This project implements **Feature #1: AI Recommendations** for your smart hospital system.
It uses:
- **Flask** for the backend
- **HTML/CSS/JavaScript** for the frontend
- **ILMU API** for AI-generated suggestions
- **CSV files** as the data source

## Project structure

```bash
smart_hospital_project/
│
├── app.py
├── ai_service.py
├── analytics.py
├── config.py
├── requirements.txt
├── .env.example
├── data/
│   ├── daily_demand_summary.csv
│   ├── specialization_summary.csv
│   └── merged_hospital_data.csv
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```

## 1. Open in VS Code
Extract the folder and open it in VS Code.

## 2. Create a virtual environment
### Windows PowerShell
```powershell
python -m venv venv
venv\Scripts\activate
```

If `python` does not work on your PC, use:
```powershell
py -3 -m venv venv
venv\Scripts\activate
```

## 3. Install packages
```powershell
pip install -r requirements.txt
```

## 4. Add your ILMU API key
Create a file named `.env` in the project root:
```env
ILMU_API_KEY=your_real_key_here
ILMU_BASE_URL=https://api.ilmu.ai/v1
ILMU_MODEL=nemo-super
```

## 5. Run the app
```powershell
python app.py
```

Then open:
```text
http://127.0.0.1:5000
```

## 6. How it works
- `analytics.py` reads your hospital CSV files.
- It calculates a simple hospital condition summary.
- `ai_service.py` sends that summary to ILMU API.
- ILMU returns 3 recommendation cards.
- If the API key is missing or the API fails, the system still works using fallback rule-based suggestions.

## API endpoints
- `GET /api/health` → test if backend is running
- `GET /api/context` → current zone and wait-time summary
- `GET /api/recommendations` → 3 AI suggestions

## Notes
- This version focuses only on **Feature #1** as requested.
- The frontend is designed to look close to your provided mockup.
- Later, you can add cost-impact, what-if simulation, alerts, and shift planning as separate endpoints.
