import requests
import subprocess
import os

# === CONFIG ===
REPO = "ufs-community/ufs-weather-model"
BRANCH = "develop"
HASH_FILE = ".last_upstream_hash"
WORKFLOW_NAME = "regression-metrics.yml"

# === GET LATEST COMMIT HASH FROM GITHUB API ===
url = f"https://api.github.com/repos/{REPO}/commits/{BRANCH}"
headers = {"Accept": "application/vnd.github.v3+json"}
response = requests.get(url, headers=headers)
latest_hash = response.json()["sha"]

# === READ PREVIOUS HASH ===
prev_hash = ""
if os.path.exists(HASH_FILE):
    with open(HASH_FILE, "r") as f:
        prev_hash = f.read().strip()

# === COMPARE AND TRIGGER WORKFLOW ===
if latest_hash != prev_hash:
    print(f"🔄 New upstream commit detected: {latest_hash}")
    subprocess.run([
        "gh", "workflow", "run", WORKFLOW_NAME
    ], check=True)
    with open(HASH_FILE, "w") as f:
        f.write(latest_hash)
else:
    print("✅ No new upstream commits. Skipping.")
