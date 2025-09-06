import os
import yaml
import csv
import subprocess
from collections import defaultdict

UFS_REPO = "/work/noaa/epic/jongkim/UFS-RT/ufs-weather-model"
ATM_YAML = "/work/noaa/epic/jongkim/UFS-RT/ufs-wm-metrics/tests-yamls/configs/by_app/atm.yaml"
MACHINES = ["orion", "hera", "hercules"]
NUM_COMMITS = 10
OUTPUT_DIR = "wall_time_by_case"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_recent_hashes():
    subprocess.run(["git", "-C", UFS_REPO, "fetch", "origin", "develop"])
    result = subprocess.run(
        ["git", "-C", UFS_REPO, "log", "origin/develop", "-n", str(NUM_COMMITS), "--pretty=format:%h"],
        capture_output=True, text=True
    )
    return result.stdout.strip().splitlines()

def load_atm_tests():
    with open(ATM_YAML) as f:
        config = yaml.safe_load(f)

    case_map = defaultdict(set)
    print("🔍 Scanning atm.yaml for test cases...")
    for app_name, app_config in config.items():
        tests = app_config.get("tests", [])
        for entry in tests:
            if isinstance(entry, dict):
                for test_name in entry.keys():
                    for machine in MACHINES:
                        case_map[test_name].add(machine)
                    print(f"  • {test_name:<30} (from app: {app_name})")
    return case_map

def normalize_test_name(name):
    for suffix in ["_intel", "_gnu", "_pgi", "_nvhpc"]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name

def parse_wall_time(line):
    if "[" in line and "]" in line:
        try:
            time_block = line.split("[")[1].split("]")[0]
            time_str = time_block.split(",")[0].strip()
            h, m = map(int, time_str.split(":"))
            return h * 60 + m
        except Exception:
            return None
    return None

def collect_wall_times(hashes, case_map):
    matrix = defaultdict(lambda: defaultdict(dict))  # case → hash → machine → time
    for h in hashes:
        print(f"\n🔎 Checking out commit: {h}")
        subprocess.run(["git", "-C", UFS_REPO, "checkout", h], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        for machine in MACHINES:
            log_path = os.path.join(UFS_REPO, "tests", "logs", f"RegressionTests_{machine}.log")
            if not os.path.exists(log_path):
                print(f"  ⚠️ Missing log for {machine} at {h}")
                continue
            with open(log_path) as f:
                for line in f:
                    if "PASS -- TEST" in line and "[" in line:
                        try:
                            raw_name = line.split("TEST '")[1].split("'")[0]
                            normalized = normalize_test_name(raw_name)
                            wall_time = parse_wall_time(line)

                            print(f"  🔍 Found in log: {raw_name:<35} → normalized: {normalized:<30}", end="")

                            if normalized in case_map:
                                if machine in case_map[normalized]:
                                    if wall_time:
                                        matrix[normalized][h][machine] = wall_time
                                        print(f" ✅ matched for {machine:<8} | {wall_time:>4} min")
                                    else:
                                        print(" ⚠️ matched but no wall time")
                                else:
                                    print(f" ⚠️ test exists but not assigned to {machine}")
                            else:
                                print(" ❌ no match in atm.yaml")
                        except Exception:
                            continue
    return matrix

def write_csv_per_case(matrix, hashes):
    for case, hash_map in matrix.items():
        path = os.path.join(OUTPUT_DIR, f"{case}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Hash"] + MACHINES)
            for h in hashes:
                row = [h] + [hash_map.get(h, {}).get(m, "") for m in MACHINES]
                writer.writerow(row)
        print(f"📄 Dumped: {path}")

if __name__ == "__main__":
    hashes = get_recent_hashes()
    case_map = load_atm_tests()
    if not case_map:
        print("⚠️ No test cases found in atm.yaml")
    else:
        matrix = collect_wall_times(hashes, case_map)
        write_csv_per_case(matrix, hashes)
        print(f"\n✅ All wall time matrices saved to {OUTPUT_DIR}/")
