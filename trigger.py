import requests
import os
import datetime

REPO = "ufs-community/ufs-weather-model"
BRANCH = "develop"
HASH_FILE = ".last_hash"
LOG_FILE = "trigger.log"

def get_latest_hash(repo=REPO, branch=BRANCH):
    url = f"https://api.github.com/repos/{repo}/commits/{branch}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()["sha"]
    except Exception as e:
        print(f"[ERROR] Failed to fetch latest hash: {e}")
        return None

def has_new_commit(latest_hash, hash_file=HASH_FILE):
    try:
        with open(hash_file, "r") as f:
            stored_hash = f.read().strip()
    except FileNotFoundError:
        stored_hash = ""

    if latest_hash != stored_hash:
        with open(hash_file, "w") as f:
            f.write(latest_hash)
        return True
    return False

def log_trigger_event(hash_val, log_file=LOG_FILE):
    with open(log_file, "a") as log:
        log.write(f"{datetime.datetime.now().isoformat()} - Triggered by hash: {hash_val}\n")
