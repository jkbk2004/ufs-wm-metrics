import os
import yaml
import csv
import subprocess
import matplotlib.pyplot as plt
from collections import defaultdict

# Config
UFS_REPO = "/work/noaa/epic/jongkim/UFS-RT/ufs-weather-model"
BY_APP_DIR = "/work/noaa/epic/jongkim/UFS-RT/ufs-wm-metrics/tests-yamls/configs/by_app"
RESULTS_DIR = "results/by_app"
MACHINES = ["orion", "hera", "gaeac6"]
NUM_COMMITS = 50

def get_recent_hashes():
    subprocess.run(["git", "-C", UFS_REPO, "fetch", "origin", "develop"])
    result = subprocess.run(
        ["git", "-C", UFS_REPO, "log", "origin/develop", "-n", str(NUM_COMMITS), "--pretty=format:%h"],
        capture_output=True, text=True
    )
    return result.stdout.strip().splitlines()

def normalize_test_name(name):
    for suffix in ["_intel", "_gnu", "_pgi", "_nvhpc"]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name

def parse_core_hour(line):
    try:
        time_block = line.split("[")[1].split("]")[0]
        core_str = time_block.split(",")[1].strip()
        h, m = map(int, core_str.split(":"))
        return h * 60 + m
    except:
        return None

def parse_memory_mb(line):
    try:
        mem_str = line.split("(")[1].split("MB")[0].strip()
        return int(mem_str)
    except:
        return None

def load_tests_from_yaml(yaml_path):
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    case_map = defaultdict(set)
    for app_name, app_config in config.items():
        for entry in app_config.get("tests", []):
            if isinstance(entry, dict):
                for test_name in entry.keys():
                    for machine in MACHINES:
                        case_map[test_name].add(machine)
    return case_map

def collect_metrics(hashes, case_map):
    core_matrix = defaultdict(lambda: defaultdict(dict))  # case → hash → machine → core_hour
    mem_matrix = defaultdict(lambda: defaultdict(dict))   # case → hash → machine → memory_mb
    for h in hashes:
        subprocess.run(["git", "-C", UFS_REPO, "checkout", h], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for machine in MACHINES:
            log_path = os.path.join(UFS_REPO, "tests", "logs", f"RegressionTests_{machine}.log")
            if not os.path.exists(log_path):
                continue
            with open(log_path) as f:
                for line in f:
                    if "PASS -- TEST" in line and "[" in line and "(" in line:
                        try:
                            raw_name = line.split("TEST '")[1].split("'")[0]
                            normalized = normalize_test_name(raw_name)
                            core_hour = parse_core_hour(line)
                            memory_mb = parse_memory_mb(line)
                            if normalized in case_map and machine in case_map[normalized]:
                                if core_hour:
                                    core_matrix[normalized][h][machine] = core_hour
                                if memory_mb:
                                    mem_matrix[normalized][h][machine] = memory_mb
                        except:
                            continue
    return core_matrix, mem_matrix

def write_csv_and_plot(matrix, hashes, out_dir, suffix="", ylabel=""):
    os.makedirs(out_dir, exist_ok=True)
    for case, hash_map in matrix.items():
        csv_path = os.path.join(out_dir, f"{case}{suffix}.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Hash"] + MACHINES)
            for h in hashes:
                row = [h] + [hash_map.get(h, {}).get(m, "") for m in MACHINES]
                writer.writerow(row)

        # Plot
        plt.figure(figsize=(12, 6))
        for machine in MACHINES:
            y = [hash_map.get(h, {}).get(machine, None) for h in hashes]
            if any(y):
                plt.plot(hashes, y, label=machine, marker="o")
        plt.title(f"{ylabel} for {case}")
        plt.xlabel("Commit Hash")
        plt.ylabel(ylabel)
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        png_path = csv_path.replace(".csv", ".png")
        plt.savefig(png_path)
        plt.close()

def process_app_yaml(yaml_file, hashes):
    app_name = os.path.splitext(os.path.basename(yaml_file))[0]
    print(f"\n🔍 Processing app: {app_name}")
    case_map = load_tests_from_yaml(yaml_file)
    core_matrix, mem_matrix = collect_metrics(hashes, case_map)

    walltime_dir = os.path.join(RESULTS_DIR, "walltime", app_name)
    memsize_dir = os.path.join(RESULTS_DIR, "memsize", app_name)

    write_csv_and_plot(core_matrix, hashes, walltime_dir, "", "Core Hours (minutes)")
    write_csv_and_plot(mem_matrix, hashes, memsize_dir, "_memory", "Max Memory (MB)")

if __name__ == "__main__":
    hashes = get_recent_hashes()
    yaml_files = [os.path.join(BY_APP_DIR, f) for f in os.listdir(BY_APP_DIR) if f.endswith(".yaml")]
    for yaml_file in yaml_files:
        process_app_yaml(yaml_file, hashes)
    print(f"\n✅ All results saved to results/by_app/")
