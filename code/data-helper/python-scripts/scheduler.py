from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess
import os

# ==== CONFIG ====
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = {
    "mixer_check": os.path.join(BASE_PATH, "Heuristic-checks", "Mixer_check.py"),
    "peeling_chains": os.path.join(BASE_PATH, "Heuristic-checks", "Peeling_chains.py"),
    "structuring_check": os.path.join(BASE_PATH, "Heuristic-checks", "Structuring_check.py"),
    "ofac_sanctions": os.path.join(BASE_PATH, "OFAC-Sanctions", "OFACSanctionScript.py"),
    "third_party_data": os.path.join(BASE_PATH, "Third-Party-Sources", "third_party_data.py"),
}

# ==== HELPER ====
def run_script(script_path):
    try:
        print(f"[INFO] Running {os.path.basename(script_path)} ...")
        result = subprocess.run(["python", script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[SUCCESS] {os.path.basename(script_path)}\n{result.stdout}")
        else:
            print(f"[ERROR] {os.path.basename(script_path)}\n{result.stderr}")
    except Exception as e:
        print(f"[EXCEPTION] Failed to run {os.path.basename(script_path)}: {e}")

# ==== SCHEDULER ====
scheduler = BlockingScheduler()

# Heuristic checks → every 6 hours
scheduler.add_job(lambda: run_script(SCRIPTS["mixer_check"]), "interval", hours=6)
scheduler.add_job(lambda: run_script(SCRIPTS["peeling_chains"]), "interval", hours=6)
scheduler.add_job(lambda: run_script(SCRIPTS["structuring_check"]), "interval", hours=6)

# OFAC sanctions list update → once a day
scheduler.add_job(lambda: run_script(SCRIPTS["ofac_sanctions"]), "interval", days=1)

# Third-party data update → every 12 hours
scheduler.add_job(lambda: run_script(SCRIPTS["third_party_data"]), "interval", hours=12)

print("[INFO] Scheduler started. Press Ctrl+C to exit.")
scheduler.start()
