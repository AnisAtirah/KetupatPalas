import os
from pathlib import Path

import pandas as pd
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name)


def get_latest_day_frames():
    ops = load_csv("pediatrics_daily_operations_clean.csv")
    doc = load_csv("pediatrics_doctor_availability_daily.csv")
    nurse = load_csv("pediatrics_nurse_availability_daily.csv")
    bed = load_csv("pediatrics_Bed.csv")

    for df in (ops, doc, nurse, bed):
        df["date"] = pd.to_datetime(df["date"])

    latest_date = ops["date"].max()

    ops_today = ops[ops["date"] == latest_date]
    doc_today = doc[doc["date"] == latest_date]
    nurse_today = nurse[nurse["date"] == latest_date]
    bed_today = bed[bed["date"] == latest_date]

    return latest_date, ops_today, doc_today, nurse_today, bed_today


def simulate(user_input):
    latest_date, ops_today, doc_today, nurse_today, bed_today = get_latest_day_frames()

    ops_row = ops_today.iloc[0]
    doc_row = doc_today.iloc[0]
    nurse_row = nurse_today.iloc[0]

    patients = int(ops_row.get("appointments", 0))
    doctors = int(doc_row.get("scheduled_doctors", 0))
    nurses = int(nurse_row.get("scheduled_nurses", 0))
    beds = int(bed_today["available_beds"].sum()) if "available_beds" in bed_today.columns else 0

    add_doctors = int(user_input.get("add_doctors", 0))
    add_nurses = int(user_input.get("add_nurses", 0))
    add_beds = int(user_input.get("add_beds", 0))

    total_doctors = max(doctors + add_doctors, 1)
    total_nurses = max(nurses + add_nurses, 1)
    total_beds = max(beds + add_beds, 1)

    workload = float(ops_row.get("workload_score", patients))

    doctor_load = patients / total_doctors
    nurse_load = patients / total_nurses

    estimated_bed_need = int((patients * 0.20) + (workload * 0.05))
    bed_gap = max(0, estimated_bed_need - total_beds)

    wait_time = round(
        10
        + (doctor_load * 5)
        + (nurse_load * 2)
        + (bed_gap * 2)
        + (workload * 0.10),
        1,
    )

    patients_served = int(
        min(
            patients,
            (total_doctors * 12) + (total_nurses * 4) + (total_beds * 0.6),
        )
    )

    cost = (add_doctors * 500) + (add_nurses * 220) + (add_beds * 100)

    status = "Stable"
    if wait_time > 90 or doctor_load > 18:
        status = "High overload"
    elif wait_time > 60 or doctor_load > 12:
        status = "Moderate pressure"

    return {
        "date": str(latest_date.date()),
        "real_inputs": {
            "patients": patients,
            "doctors": doctors,
            "nurses": nurses,
            "beds": beds,
        },
        "after_change": {
            "doctors": total_doctors,
            "nurses": total_nurses,
            "beds": total_beds,
        },
        "results": {
            "wait_time": wait_time,
            "patients_served": patients_served,
            "doctor_load": round(doctor_load, 2),
            "nurse_load": round(nurse_load, 2),
            "estimated_bed_need": estimated_bed_need,
            "cost": cost,
            "status": status,
        },
    }


def fallback_recommendation(sim):
    r = sim["results"]

    analysis = (
        f"Estimated wait time is {r['wait_time']} minutes and the department can serve about "
        f"{r['patients_served']} patients. Doctor load is {r['doctor_load']} and nurse load is {r['nurse_load']}. "
    )

    if r["status"] == "High overload":
        return analysis + (
            "This scenario is under high pressure. Adding doctors and beds is recommended "
            "to reduce delays and improve patient coverage."
        )

    if r["status"] == "Moderate pressure":
        return analysis + (
            "This scenario is manageable but still under pressure. Adding one more doctor or nurse "
            "may improve flow and reduce waiting time."
        )

    return analysis + (
        "This scenario appears stable. Current resources are sufficient, "
        "but demand should continue to be monitored."
    )


def ask_ai(sim):
    api_key = os.getenv("ZAI_API_KEY")
    model = os.getenv("ZAI_MODEL", "nemo-super")
    base_url = os.getenv("ZAI_BASE_URL", "https://api.ilmu.ai/v1")
    url = base_url.rstrip("/") + "/chat/completions"

    if not api_key:
        return fallback_recommendation(sim)

    real = sim["real_inputs"]
    changed = sim["after_change"]
    r = sim["results"]

    prompt = f"""
You are an assistant for a Pediatrics hospital resource dashboard.

Analyze this simulation result and give:
1. A short performance analysis
2. A short recommendation
3. A short cost-impact comment

Use simple English.
Keep it under 120 words.

Current real state:
- Patients: {real['patients']}
- Doctors: {real['doctors']}
- Nurses: {real['nurses']}
- Beds: {real['beds']}

After what-if changes:
- Doctors: {changed['doctors']}
- Nurses: {changed['nurses']}
- Beds: {changed['beds']}

Simulation result:
- Wait time: {r['wait_time']} minutes
- Patients served: {r['patients_served']}
- Doctor load: {r['doctor_load']}
- Nurse load: {r['nurse_load']}
- Estimated bed need: {r['estimated_bed_need']}
- Added cost: RM{r['cost']}
- Status: {r['status']}

Explain whether this scenario improves hospital performance and why.
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2500,
        "temperature": 0.4,
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        print("AI timeout: server took too long to respond")
        return fallback_recommendation(sim)
    except Exception as e:
        if hasattr(e, "response") and e.response is not None:
            print("AI status:", e.response.status_code)
            print("AI body:", e.response.text)
        print("AI error:", e)
        return fallback_recommendation(sim)


@app.get("/api/summary")
def summary():
    sim = simulate({})
    return jsonify(sim)


@app.post("/api/simulate")
def api_simulate():
    user_input = request.get_json(silent=True) or {}
    return jsonify(simulate(user_input))


@app.post("/api/recommendation")
def api_recommendation():
    user_input = request.get_json(silent=True) or {}
    sim = simulate(user_input)
    rec = ask_ai(sim)

    return jsonify({
        "simulation": sim,
        "recommendation": rec
    })


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)