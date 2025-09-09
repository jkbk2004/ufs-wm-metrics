import requests
import os

# === CONFIG ===
REPO_OWNER = "jkbk2004"
REPO_NAME = "ufs-wm-metrics"
WORKFLOW_FILE = "regression-metrics.yml"  # Must match the filename in .github/workflows/
BRANCH = "main"
UPSTREAM_REPO = "ufs-community/ufs-weather-model"
UPSTREAM_BRANCH = "develop"
HASH_FILE = ".last_upstream_hash"

# === AUTH ===
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN not found in environment.")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# === GET LATEST COMMIT HASH FROM UPSTREAM ===
commit_url = f"https://api.github.com/repos/{UPSTREAM_REPO}/commits/{UPSTREAM_BRANCH}"
latest_hash = requests.get(commit_url, headers=headers).json()["sha"]

# === READ PREVIOUS HASH ===
prev_hash = ""
if os.path.exists(HASH_FILE):
    with open(HASH_FILE, "r") as f:
        prev_hash = f.read().strip()

# === COMPARE AND TRIGGER WORKFLOW ===
if latest_hash != prev_hash:
    print(f"🔄 New upstream commit detected: {latest_hash}")

    # Trigger workflow via GitHub API
    dispatch_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    payload = {
        "ref": BRANCH
    }

    response = requests.post(dispatch_url, headers=headers, json=payload)
    if response.status_code == 204:
        print("🚀 Regression Metrics workflow triggered successfully.")
        with open(HASH_FILE, "w") as f:
            f.write(latest_hash)
    else:
        print(f"❌ Failed to trigger workflow: {response.status_code}")
        print(response.text)
else:
    print("✅ No new upstream commits. Skipping.")
