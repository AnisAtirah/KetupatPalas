from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


@dataclass
class RecommendationContext:
    zone: str
    status: str
    current_wait: float
    avg_wait: float
    today_appointments: int
    peak_specialization: str
    peak_load: float
    doctor_utilization: float
    nurse_utilization: float
    bed_occupancy: float
    available_beds: int
    available_doctors: int
    available_nurses: int
    explanation_points: List[str]
    suggestions: List[Dict[str, Any]]


@lru_cache(maxsize=1)
def load_data() -> Dict[str, pd.DataFrame]:
    daily = pd.read_csv(DATA_DIR / "pediatrics_daily_operations_clean.csv")
    spec = pd.read_csv(DATA_DIR / "pediatrics_specialization_summary.csv")
    merged = pd.read_csv(DATA_DIR / "pediatrics_merged_hospital_data.csv")
    doctor_daily = pd.read_csv(DATA_DIR / "pediatrics_doctor_availability_daily.csv")
    nurse_daily = pd.read_csv(DATA_DIR / "pediatrics_nurse_availability_daily.csv")
    bed = pd.read_csv(DATA_DIR / "pediatrics_Bed.csv")
    billing_summary = pd.read_csv(DATA_DIR / "pediatrics_billing_summary.csv")

    daily["date"] = pd.to_datetime(daily["date"])
    doctor_daily["date"] = pd.to_datetime(doctor_daily["date"])
    nurse_daily["date"] = pd.to_datetime(nurse_daily["date"])
    bed["date"] = pd.to_datetime(bed["date"])
    merged["Date"] = pd.to_datetime(merged["Date"])

    return {
        "daily": daily.sort_values("date").reset_index(drop=True),
        "spec": spec,
        "merged": merged.sort_values("Date").reset_index(drop=True),
        "doctor_daily": doctor_daily.sort_values("date").reset_index(drop=True),
        "nurse_daily": nurse_daily.sort_values("date").reset_index(drop=True),
        "bed": bed.sort_values("date").reset_index(drop=True),
        "billing_summary": billing_summary,
    }


@lru_cache(maxsize=1)
def build_recommendation_context() -> RecommendationContext:
    data = load_data()

    daily = data["daily"]
    spec = data["spec"]
    doctor_daily = data["doctor_daily"]
    nurse_daily = data["nurse_daily"]
    bed = data["bed"]
    billing_summary = data["billing_summary"]

    recent_daily = daily.tail(7).copy()
    current_wait = float(recent_daily["estimated_wait_minutes"].mean())
    avg_wait = float(daily["estimated_wait_minutes"].mean())
    today_appointments = int(round(recent_daily["appointments"].mean()))

    latest_doctor = doctor_daily.tail(7).copy()
    latest_nurse = nurse_daily.tail(7).copy()
    latest_bed = bed[bed["date"] == bed["date"].max()].copy()

    doctor_utilization = float(latest_doctor["doctor_utilization_rate"].mean())
    nurse_utilization = float(latest_nurse["nurse_utilization_rate"].mean())

    total_beds = int(latest_bed["total_beds"].sum())
    occupied_beds = int(latest_bed["occupied_beds"].sum())
    available_beds = int(latest_bed["available_beds"].sum())
    available_doctors = int(round(latest_doctor["available_doctors"].mean()))
    available_nurses = int(round(latest_nurse["available_nurses"].mean()))
    bed_occupancy = (occupied_beds / total_beds) if total_beds else 0.0

    peak_row = spec.sort_values("appointments_per_doctor", ascending=False).iloc[0]
    peak_specialization = str(peak_row["Specialization"])
    peak_load = float(peak_row["appointments_per_doctor"])

    if current_wait >= 50 or bed_occupancy >= 0.85 or nurse_utilization >= 0.92:
        zone = "Red Zone"
        status = "High pressure"
    elif current_wait >= 38 or bed_occupancy >= 0.75 or doctor_utilization >= 0.75:
        zone = "Yellow Zone"
        status = "Busy but manageable"
    else:
        zone = "Green Zone"
        status = "Stable"

    monthly_revenue = float(billing_summary["total_amount"].mean())

    explanation_points = [
        f"Average pediatric waiting time over the latest 7 days is {current_wait:.1f} minutes.",
        f"Overall pediatric average waiting time is {avg_wait:.1f} minutes.",
        f"Recent pediatric appointment demand is about {today_appointments} patients per day.",
        f"{peak_specialization} has the highest load at {peak_load:.2f} appointments per doctor.",
        f"Doctor utilization is {doctor_utilization * 100:.1f}% and nurse utilization is {nurse_utilization * 100:.1f}%.",
        f"Current pediatric bed occupancy is {bed_occupancy * 100:.1f}% with {available_beds} beds available.",
        f"Average monthly pediatric billing is RM {monthly_revenue:,.0f}.",
    ]

    suggestions = _rule_based_suggestions(
        zone=zone,
        current_wait=current_wait,
        peak_specialization=peak_specialization,
        peak_load=peak_load,
        doctor_utilization=doctor_utilization,
        nurse_utilization=nurse_utilization,
        bed_occupancy=bed_occupancy,
        available_beds=available_beds,
        available_doctors=available_doctors,
        available_nurses=available_nurses,
    )

    return RecommendationContext(
        zone=zone,
        status=status,
        current_wait=current_wait,
        avg_wait=avg_wait,
        today_appointments=today_appointments,
        peak_specialization=peak_specialization,
        peak_load=peak_load,
        doctor_utilization=doctor_utilization,
        nurse_utilization=nurse_utilization,
        bed_occupancy=bed_occupancy,
        available_beds=available_beds,
        available_doctors=available_doctors,
        available_nurses=available_nurses,
        explanation_points=explanation_points,
        suggestions=suggestions,
    )


def _rule_based_suggestions(
    zone: str,
    current_wait: float,
    peak_specialization: str,
    peak_load: float,
    doctor_utilization: float,
    nurse_utilization: float,
    bed_occupancy: float,
    available_beds: int,
    available_doctors: int,
    available_nurses: int,
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []

    if zone == "Red Zone":
        suggestions.append(
            {
                "title": "Add 2 temporary pediatric beds",
                "explanation": (
                    f"Pediatric bed occupancy is {bed_occupancy * 100:.1f}% and only {available_beds} beds remain, "
                    "so adding temporary bed capacity can reduce admission bottlenecks."
                ),
                "priority": "High",
            }
        )
        suggestions.append(
            {
                "title": f"Reassign 1 doctor to {peak_specialization}",
                "explanation": (
                    f"{peak_specialization} has the highest workload at {peak_load:.2f} appointments per doctor. "
                    "A temporary doctor reassignment can reduce service backlog faster."
                ),
                "priority": "High",
            }
        )
        suggestions.append(
            {
                "title": "Assign extra pediatric nurse support",
                "explanation": (
                    f"Nurse utilization is {nurse_utilization * 100:.1f}%, which suggests the nursing team is near full capacity "
                    "during recent operations."
                ),
                "priority": "High",
            }
        )

    elif zone == "Yellow Zone":
        if available_beds <= 5:
            suggestions.append(
                {
                    "title": "Prepare overflow pediatric beds",
                    "explanation": (
                        f"Only {available_beds} pediatric beds are currently available, so preparing overflow beds helps "
                        "prevent sudden congestion."
                    ),
                    "priority": "High",
                }
            )
        else:
            suggestions.append(
                {
                    "title": "Monitor pediatric bed allocation closely",
                    "explanation": (
                        f"Bed occupancy is {bed_occupancy * 100:.1f}%, so closer monitoring can prevent the unit from "
                        "moving into a high-pressure state."
                    ),
                    "priority": "Medium",
                }
            )

        suggestions.append(
            {
                "title": f"Support {peak_specialization} during peak hours",
                "explanation": (
                    f"{peak_specialization} is the busiest pediatric specialty with {peak_load:.2f} appointments per doctor, "
                    "so targeted support should improve flow."
                ),
                "priority": "High",
            }
        )

        suggestions.append(
            {
                "title": "Optimize appointment staggering",
                "explanation": (
                    f"Recent average waiting time is {current_wait:.1f} minutes. Spacing pediatric appointments more evenly "
                    "can reduce queue spikes."
                ),
                "priority": "Medium",
            }
        )

    else:
        suggestions.append(
            {
                "title": "Maintain current pediatric staffing",
                "explanation": (
                    f"Current waiting time is {current_wait:.1f} minutes and operations remain stable, so no urgent staffing increase is needed."
                ),
                "priority": "Low",
            }
        )
        suggestions.append(
            {
                "title": f"Keep standby coverage for {peak_specialization}",
                "explanation": (
                    f"{peak_specialization} still shows the highest specialty workload, so standby support is useful if daily demand rises."
                ),
                "priority": "Medium",
            }
        )
        suggestions.append(
            {
                "title": "Review resource utilization every shift",
                "explanation": (
                    f"Doctors are at {doctor_utilization * 100:.1f}% utilization and nurses at {nurse_utilization * 100:.1f}%, "
                    "so routine monitoring helps keep the department stable."
                ),
                "priority": "Medium",
            }
        )

    return suggestions


def build_prompt_payload() -> Dict[str, Any]:
    context = build_recommendation_context()

    return {
        "department": "Pediatrics",
        "zone": context.zone,
        "status": context.status,
        "current_wait": round(context.current_wait, 1),
        "avg_wait": round(context.avg_wait, 1),
        "today_appointments": context.today_appointments,
        "peak_specialization": context.peak_specialization,
        "peak_load": round(context.peak_load, 2),
        "doctor_utilization": round(context.doctor_utilization, 3),
        "nurse_utilization": round(context.nurse_utilization, 3),
        "bed_occupancy": round(context.bed_occupancy, 3),
        "available_beds": context.available_beds,
        "available_doctors": context.available_doctors,
        "available_nurses": context.available_nurses,
        "facts": context.explanation_points,
        "rule_based_suggestions": context.suggestions,
    }