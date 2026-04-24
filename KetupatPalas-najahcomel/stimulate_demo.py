import time
from costvsefficiency import simulate_once

while True:
    time.sleep(10)
    data = simulate_once("normal")
    print("\n--- HOSPITAL UPDATE ---")
    print("State:", data["state"])
    print("Cost Change:", data["cost_change"])
    print("Waiting Time Change:", data["waiting_time_change"])
    print("Interpretation:", data["interpretation"])
    print("Insight:", data["insight"])