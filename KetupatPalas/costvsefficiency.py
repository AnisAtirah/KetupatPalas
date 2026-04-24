import random

cost_weights = {
    "doctor": 800,
    "nurse": 100,
    "icu_patient": 1000,
    "ward_patient": 70,
    "er_patient": 90,
}

pressure = {
    "normal": 1,
    "busy": 1.5,
    "critical": 2.5
}

state = {
    "doctors": 3,
    "nurses": 8,
    "icu_patients": 2,
    "ward_patients": 10,
    "er_patients": 5,
}

previous_state = state.copy()
history = []

def calculate_cost(s):
    return (
        s["doctors"] * cost_weights["doctor"] +
        s["nurses"] * cost_weights["nurse"] +
        s["icu_patients"] * cost_weights["icu_patient"] +
        s["ward_patients"] * cost_weights["ward_patient"] +
        s["er_patients"] * cost_weights["er_patient"]
    )

def calculate_waiting_time(s):
    load = s["icu_patients"] * 3 + s["ward_patients"] + s["er_patients"]
    staff = s["doctors"] + s["nurses"]
    ratio = load / staff
    if ratio > 5:
        ratio *= 1.5
    return ratio * 10

def update_state(s, level="normal"):
    s = s.copy()  # IMPORTANT: don't mutate the original
    p = pressure[level]
    s["er_patients"] += int(random.randint(0, 2) * p)
    s["ward_patients"] += int(random.randint(0, 2) * p)
    s["icu_patients"] += int(random.randint(0, 2) * p)
    s["doctors"] += int(random.choice([-4, -3, -2, -1, 0, 1, 2, 3, 4, 5]) * p)
    s["nurses"] += int(random.choice([-2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8]) * p)
    s["ward_patients"] = min(s["ward_patients"], 50)
    s["icu_patients"] = max(0, min(s["icu_patients"], 10))
    s["er_patients"] = max(0, s["er_patients"])
    s["nurses"] = max(1, min(s["nurses"], 20))
    s["doctors"] = max(1, min(s["doctors"], 10))
    return s

def analyze(prev, curr):
    return {
        "cost_change": calculate_cost(curr) - calculate_cost(prev),
        "waiting_time_change": calculate_waiting_time(curr) - calculate_waiting_time(prev),
        "current_cost": calculate_cost(curr),
        "current_waiting_time": calculate_waiting_time(curr),
    }

def interpret(result):
    msg = []
    msg.append("Cost increased ⚠️" if result["cost_change"] > 0 else "Cost decreased ✅")
    msg.append("Waiting time increased ⏳" if result["waiting_time_change"] > 0 else "Waiting time improved 🚀")
    return " | ".join(msg)

def insight(h):
    if len(h) < 2:
        return "Collecting baseline data..."
    return "Cost trend is increasing." if h[-1] > h[-2] else "Cost trend is stable or improving."

def simulate_once(level="normal"):
    global state, previous_state, history

    current_state = update_state(state, level)
    result = analyze(previous_state, current_state)
    history.append(result["current_cost"])

    response = {
        "cost_change": result["cost_change"],
        "waiting_time_change": result["waiting_time_change"],
        "current_cost": result["current_cost"],
        "current_waiting_time": result["current_waiting_time"],
        "patients_served": current_state["icu_patients"] + current_state["ward_patients"] + current_state["er_patients"],
        "wait_time_reduction": round(abs(result["waiting_time_change"]) / 60, 2),
        "cost_increase_percent": round((abs(result["cost_change"]) / max(result["current_cost"], 1)) * 100, 2),
        "interpretation": interpret(result),
        "insight": insight(history),
        "state": current_state
    }

    previous_state = current_state.copy()
    state = current_state.copy()

    return response