import os
import yaml
import csv
from collections import defaultdict

# Paths
UFS_REPO = "/work/noaa/epic/jongkim/UFS-RT/plots_reg/ufs-weather-model"
LOG_DIR = os.path.join(UFS_REPO, "tests/logs")
ATM_YAML = "/work/noaa/epic/jongkim/UFS-RT/plots_reg/ufs-wm-metrics/tests-yamls/configs/by_app/atm.yaml"
MACHINES = ["orion", "hera", "hercules"]
NUM_COMMITS = 10
OUTPUT_DIR = "wall_time_by_case"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_recent_hashes():
    os.system(f"git -C {UFS_REPO} fetch origin develop")
    hashes = os.popen(f"git -C {UFS_REPO} log origin/develop -n {NUM_COMMITS} --pretty=format:'%h'").read().splitlines()
    return [h.strip("'") for h in hashes]

def load_atm_tests():
    with open(ATM_YAML) as f:
        config = yaml.safe_load(f)
    case_map = defaultdict(set)
    print("🔍 Test cases found in atm.yaml:")
    for entry in config.get("tests", []):
        name = entry.get("name")
        machine = entry.get("machine", "").lower()
        if name and machine in MACHINES:
            case_map[name].add(machine)
            print(f"  • {name:<30} (machine: {machine})")
    return case_map

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
        print(f"\n🔎 Processing commit: {h}")
        for machine in MACHINES:
            log_path = os.path.join(LOG_DIR, f"RegressionTests_{machine}_{h}.log")
            if not os.path.exists(log_path):
                print(f"  ⚠️ Missing log for {machine} at {h}")
                continue
            with open(log_path) as f:
                for line in f:
                    if "PASS -- TEST" in line and "[" in line:
                        try:
                            test_name = line.split("TEST '")[1].split("'")[0]
                            if test_name in case_map and machine in case_map[test_name]:
                                wall_time = parse_wall_time(line)
                                if wall_time:
                                    matrix[test_name][h][machine] = wall_time
                                    print(f"  ✅ {test_name:<30} | {machine:<9} | {wall_time:>4} min")
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
