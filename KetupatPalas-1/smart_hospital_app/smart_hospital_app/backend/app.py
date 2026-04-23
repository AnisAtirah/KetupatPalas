import os
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
FRONTEND_DIR = BASE_DIR / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)


def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name)


def simulate(payload: Dict[str, Any]) -> Dict[str, Any]:
    patients = int(payload.get("patients", 80))
    doctors = max(1, int(payload.get("doctors", 4)))
    nurses = max(1, int(payload.get("nurses", 10)))
    beds = max(1, int(payload.get("beds", 20)))
    avg_complexity = float(payload.get("avg_complexity", 2.0))

    add_doctors = int(payload.get("add_doctors", 0))
    add_nurses = int(payload.get("add_nurses", 0))
    add_beds = int(payload.get("add_beds", 0))

    total_doctors = doctors + add_doctors
    total_nurses = nurses + add_nurses
    total_beds = beds + add_beds

    doctor_load = patients / total_doctors
    nurse_load = patients / total_nurses
    bed_gap = max(0, int(patients * 0.25) - total_beds)

    wait_time = round(
        15 + (doctor_load * 6) + (nurse_load * 2.5) + (avg_complexity * 8) + (bed_gap * 1.5),
        1,
    )

    patients_served = max(
        0,
        min(
            patients,
            int(total_doctors * 14 + total_nurses * 3 + total_beds * 0.5 - avg_complexity * 2),
        ),
    )

    staffing_cost = add_doctors * 500 + add_nurses * 220 + add_beds * 100

    status = "Stable"
    if wait_time > 100 or doctor_load > 18:
        status = "High overload"
    elif wait_time > 70 or doctor_load > 14:
        status = "Moderate pressure"

    return {
        "inputs": {
            "patients": patients,
            "doctors": doctors,
            "nurses": nurses,
            "beds": beds,
            "avg_complexity": avg_complexity,
            "add_doctors": add_doctors,
            "add_nurses": add_nurses,
            "add_beds": add_beds,
        },
        "results": {
            "total_doctors": total_doctors,
            "total_nurses": total_nurses,
            "total_beds": total_beds,
            "estimated_wait_time_minutes": wait_time,
            "estimated_patients_served": patients_served,
            "doctor_load": round(doctor_load, 2),
            "nurse_load": round(nurse_load, 2),
            "staffing_cost_rm": staffing_cost,
            "status": status,
        },
    }


def get_fixed_baseline() -> Dict[str, Any]:
    try:
        daily = load_csv("daily_demand_summary.csv")
        latest = daily.sort_values("Date").iloc[-1].to_dict()
        patients = int(latest.get("appointments", 80) or 80)
    except Exception:
        patients = 80

    return {
        "patients": patients,
        "doctors": 4,
        "nurses": 10,
        "beds": 20,
        "avg_complexity": 2,
    }


def build_rule_based_recommendation(sim_result: Dict[str, Any]) -> str:
    r = sim_result["results"]
    actions = []

    if r["doctor_load"] >= 16 or r["estimated_wait_time_minutes"] > 100:
        actions.append("Add at least 1 doctor because doctor workload and waiting time are too high.")
    if r["nurse_load"] > 10:
        actions.append("Add 1 to 2 nurses to improve patient flow and reduce pressure.")
    if r["total_beds"] < int(sim_result["inputs"]["patients"] * 0.25):
        actions.append("Increase bed capacity because current beds may be insufficient.")
    if not actions:
        actions.append("Current staffing is acceptable. Maintain the plan and continue monitoring demand.")

    return (
        f"Status: {r['status']}. Estimated wait time is {r['estimated_wait_time_minutes']} minutes, "
        f"with {r['estimated_patients_served']} patients served and RM{r['staffing_cost_rm']} added cost. "
        + " ".join(actions)
    )


def ask_ai(sim_result: Dict[str, Any]) -> str:
    api_key = os.getenv("ZAI_API_KEY")
    model = os.getenv("ZAI_MODEL", "nemo-super")
    base_url = os.getenv("ZAI_BASE_URL", "https://api.ilmu.ai/v1")
    url = base_url.rstrip("/") + "/chat/completions"

    if not api_key:
        return build_rule_based_recommendation(sim_result)

    r = sim_result["results"]

    prompt = f"""
Wait time: {r['estimated_wait_time_minutes']} minutes
Patients served: {r['estimated_patients_served']}
Doctor load: {r['doctor_load']}
Nurse load: {r['nurse_load']}
Added cost: RM{r['staffing_cost_rm']}
Status: {r['status']}

Give a short hospital resource recommendation in 2 sentences only.
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
        "max_tokens": 1000,
        "temperature": 0.4,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        print("AI timeout: server took too long to respond")
        return build_rule_based_recommendation(sim_result)
    except Exception as e:
        if hasattr(e, "response") and e.response is not None:
            print("AI status:", e.response.status_code)
            print("AI body:", e.response.text)
        print("AI error:", e)
        return build_rule_based_recommendation(sim_result)


@app.get("/api/summary")
def api_summary():
    baseline = get_fixed_baseline()
    return jsonify({"baseline": baseline})


@app.post("/api/simulate")
def api_simulate():
    user_input = request.get_json(force=True, silent=True) or {}
    baseline = get_fixed_baseline()

    payload = {
        "patients": baseline["patients"],
        "doctors": baseline["doctors"],
        "nurses": baseline["nurses"],
        "beds": baseline["beds"],
        "avg_complexity": baseline["avg_complexity"],
        "add_doctors": user_input.get("add_doctors", 0),
        "add_nurses": user_input.get("add_nurses", 0),
        "add_beds": user_input.get("add_beds", 0),
    }

    return jsonify(simulate(payload))


@app.post("/api/recommendation")
def api_recommendation():
    user_input = request.get_json(force=True, silent=True) or {}
    baseline = get_fixed_baseline()

    payload = {
        "patients": baseline["patients"],
        "doctors": baseline["doctors"],
        "nurses": baseline["nurses"],
        "beds": baseline["beds"],
        "avg_complexity": baseline["avg_complexity"],
        "add_doctors": user_input.get("add_doctors", 0),
        "add_nurses": user_input.get("add_nurses", 0),
        "add_beds": user_input.get("add_beds", 0),
    }

    sim_result = simulate(payload)
    recommendation = ask_ai(sim_result)

    return jsonify({
        "recommendation": recommendation,
        "simulation": sim_result
    })


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)