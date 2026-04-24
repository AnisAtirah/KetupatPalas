from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from ai_service import AIService
from analytics import build_cost_efficiency_comparison
from config import Config
from costvsefficiency import simulate_once

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)
CORS(app)

ai_service = AIService(
    api_key=app.config["ILMU_API_KEY"],
    base_url=app.config["ILMU_BASE_URL"],
    model=app.config["ILMU_MODEL"],
)

latest_dashboard_data = None


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path)


def get_fixed_baseline() -> Dict[str, Any]:
    try:
        merged = load_csv("pediatrics_merged_hospital_data.csv")
        merged["Date"] = pd.to_datetime(merged["Date"])
        patients = int(merged.sort_values("Date").iloc[-1].get("appointments", 80) or 80)
    except Exception:
        patients = 80

    try:
        doc_df = load_csv("pediatrics_doctor_availability_daily.csv")
        doctors = max(1, int(round(float(doc_df["available_doctors"].mean()))))
    except Exception:
        doctors = 4

    try:
        nurse_df = load_csv("pediatrics_nurse_availability_daily.csv")
        nurses = max(1, int(round(float(nurse_df["available_nurses"].mean()))))
    except Exception:
        nurses = 10

    try:
        bed_df = load_csv("pediatrics_Bed.csv")
        beds = max(1, int(round(float(bed_df["available_beds"].mean()))))
    except Exception:
        beds = 20

    return {
        "patients": patients,
        "doctors": doctors,
        "nurses": nurses,
        "beds": beds,
        "avg_complexity": 2,
    }


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
        15
        + (doctor_load * 6)
        + (nurse_load * 2.5)
        + (avg_complexity * 8)
        + (bed_gap * 1.5),
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


def ask_ai_for_simulation(sim_result: Dict[str, Any]) -> Dict[str, str]:
    api_key = ai_service.api_key
    model = ai_service.model
    base_url = ai_service.base_url
    url = base_url.rstrip("/") + "/chat/completions"

    if not api_key:
        raise ValueError("AI API key is missing.")

    r = sim_result["results"]

    prompt = f"""
Answer in exactly 3 short lines.
Do not use JSON.
Do not use markdown.

Analysis: explain the current performance.
Recommendation: suggest one resource action.
Cost Impact: explain the cost effect.

Data:
Wait time: {r['estimated_wait_time_minutes']} minutes
Patients served: {r['estimated_patients_served']}
Doctor load: {r['doctor_load']}
Nurse load: {r['nurse_load']}
Added cost: RM {r['staffing_cost_rm']}
Status: {r['status']}
"""

    res = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2500,
            "temperature": 0.3,
        },
        timeout=120,
    )

    res.raise_for_status()

    data = res.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")

    if not content:
        raise ValueError("AI returned empty response.")

    analysis = ""
    recommendation = ""
    cost_impact = ""

    for line in content.strip().splitlines():
        line = line.strip()

        if line.lower().startswith("analysis:"):
            analysis = line.split(":", 1)[1].strip()

        elif line.lower().startswith("recommendation:"):
            recommendation = line.split(":", 1)[1].strip()

        elif line.lower().startswith("cost impact:"):
            cost_impact = line.split(":", 1)[1].strip()

    if not analysis or not recommendation or not cost_impact:
        raise ValueError("AI response format is invalid.")

    return {
        "analysis": analysis,
        "recommendation": recommendation,
        "cost_impact": cost_impact,
    }


def get_dashboard_simulation_summary() -> Dict[str, Any]:
    global latest_dashboard_data

    if latest_dashboard_data is None:
        latest_dashboard_data = simulate_once("normal")

    data = latest_dashboard_data
    s = data["state"]

    total_patients = s["icu_patients"] + s["ward_patients"] + s["er_patients"]

    return {
        "department": "Pediatrics",
        "patients": total_patients,
        "doctors": s["doctors"],
        "nurses": s["nurses"],
        "icu_patients": s["icu_patients"],
        "ward_patients": s["ward_patients"],
        "er_patients": s["er_patients"],
        "current_cost": data["current_cost"],
        "current_waiting_time": round(data["current_waiting_time"], 1),
        "cost_change": data["cost_change"],
        "waiting_time_change": round(data["waiting_time_change"], 1),
        "patients_served": data["patients_served"],
        "interpretation": data["interpretation"],
        "insight": data["insight"],
    }


def dashboard_fallback_recommendations(summary: Dict[str, Any]) -> Dict[str, Any]:
    wait = summary["current_waiting_time"]
    patients = summary["patients"]
    doctors = summary["doctors"]
    nurses = summary["nurses"]

    return {
        "source": "simulation fallback",
        "data_summary": summary,
        "suggestions": [
            {
                "title": "Review current staffing",
                "explanation": f"Current simulation shows {doctors} doctors and {nurses} nurses handling {patients} patients.",
                "priority": "High",
            },
            {
                "title": "Monitor waiting time",
                "explanation": f"Waiting time is currently {wait} minutes, so patient flow should be monitored closely.",
                "priority": "Medium",
            },
            {
                "title": "Prepare resource support",
                "explanation": "Prepare extra staff or bed support if patient load increases.",
                "priority": "Medium",
            },
        ],
    }


@app.get("/")
def page_dashboard():
    return render_template("index.html")


@app.get("/api/health")
def api_health():
    return jsonify({"status": "ok"}), 200


@app.get("/api/context")
def api_context():
    global latest_dashboard_data

    if latest_dashboard_data is None:
        latest_dashboard_data = simulate_once("normal")

    data = latest_dashboard_data
    s = data["state"]

    total_patients = s["icu_patients"] + s["ward_patients"] + s["er_patients"]
    available_beds = max(0, 30 - s["icu_patients"] - s["ward_patients"])
    wait_time = round(data["current_waiting_time"], 1)

    if wait_time >= 70:
        zone = "Red Zone"
        status = "High pressure"
    elif wait_time >= 45:
        zone = "Yellow Zone"
        status = "Busy but manageable"
    else:
        zone = "Green Zone"
        status = "Stable"

    return jsonify({
        "zone": zone,
        "status": status,
        "current_wait": wait_time,
        "available_beds": available_beds,
        "available_doctors": s["doctors"],
        "available_nurses": s["nurses"],
        "today_appointments": total_patients,
    }), 200


@app.get("/api/recommendations")
def api_recommendations():
    summary = get_dashboard_simulation_summary()

    try:
        result = ai_service.generate_suggestions(summary)
        return jsonify(result), 200
    except Exception as exc:
        print("[DASHBOARD AI ERROR]", exc)
        return jsonify(dashboard_fallback_recommendations(summary)), 200


@app.get("/api/cost-efficiency")
def api_cost_efficiency():
    data = build_cost_efficiency_comparison()
    return jsonify(data), 200


@app.get("/api/simulate-dashboard")
def api_simulate_dashboard():
    global latest_dashboard_data

    latest_dashboard_data = simulate_once("normal")
    data = latest_dashboard_data

    return jsonify({
        "cost_change": data["cost_change"],
        "waiting_time_change": data["waiting_time_change"],
        "current_cost": data["current_cost"],
        "current_waiting_time": data["current_waiting_time"],
        "patients_served": data["patients_served"],
        "interpretation": data["interpretation"],
        "insight": data["insight"],
        "state": data["state"],
    }), 200


@app.get("/simulator")
@app.get("/simulator.html")
def page_simulator():
    return render_template("simulator.html")


@app.get("/api/summary")
def api_summary():
    return jsonify({"baseline": get_fixed_baseline()}), 200


@app.post("/api/simulate")
def api_simulate():
    user_input = request.get_json(force=True, silent=True) or {}
    baseline = get_fixed_baseline()

    payload = {
        **baseline,
        "add_doctors": user_input.get("add_doctors", 0),
        "add_nurses": user_input.get("add_nurses", 0),
        "add_beds": user_input.get("add_beds", 0),
    }

    return jsonify(simulate(payload)), 200


@app.post("/api/recommendation")
def api_recommendation():
    user_input = request.get_json(force=True, silent=True) or {}
    baseline = get_fixed_baseline()

    payload = {
        **baseline,
        "add_doctors": user_input.get("add_doctors", 0),
        "add_nurses": user_input.get("add_nurses", 0),
        "add_beds": user_input.get("add_beds", 0),
    }

    sim_result = simulate(payload)

    try:
        recommendation = ask_ai_for_simulation(sim_result)

        return jsonify({
            "analysis": recommendation["analysis"],
            "recommendation": recommendation["recommendation"],
            "cost_impact": recommendation["cost_impact"],
            "simulation": sim_result,
        }), 200

    except Exception as exc:
        print("[WHAT-IF AI ERROR]", exc)

        return jsonify({
            "error": "AI recommendation failed. Please try again later.",
            "details": str(exc),
            "simulation": sim_result,
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)