# Top of script: clone repos if missing
import os, subprocess
if not os.path.exists("ufs-weather-model"):
    subprocess.run(["git", "clone", "https://github.com/ufs-community/ufs-weather-model.git"])

# Imports
import yaml, csv, matplotlib.pyplot as plt
from collections import defaultdict
import statistics

# Config
UFS_REPO = "ufs-weather-model"
BY_APP_DIR = "tests-yamls/configs/by_app"
RESULTS_DIR = "results/by_app"
MACHINES = ["orion", "hera", "gaeac6", "hercules", "derecho", "ursa", "wcoss2", "acorn"]
NUM_COMMITS = 50

def get_recent_hashes():
    subprocess.run(["git", "-C", UFS_REPO, "fetch", "origin", "develop"])
    result = subprocess.run(
        ["git", "-C", UFS_REPO, "log", "origin/develop", "-n", str(NUM_COMMITS),
         "--pretty=format:%h|%ad|%s", "--date=short"],
        capture_output=True, text=True
    )
    return [line.strip().split("|") for line in result.stdout.strip().splitlines()]

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
    core_matrix = defaultdict(lambda: defaultdict(dict))
    mem_matrix = defaultdict(lambda: defaultdict(dict))
    for h, date, msg in hashes:
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

def detect_anomalies(values):
    clean = [v for v in values if isinstance(v, (int, float))]
    if len(clean) < 5:
        return set()
    median = statistics.median(clean)
    stdev = statistics.stdev(clean)
    return {i for i, v in enumerate(values) if isinstance(v, (int, float)) and abs(v - median) > 2 * stdev}

def write_csv_and_plot(matrix, hashes, out_dir, suffix="", ylabel=""):
    os.makedirs(out_dir, exist_ok=True)
    for case, hash_map in matrix.items():
        csv_path = os.path.join(out_dir, f"{case}{suffix}.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Hash", "Date", "Message"] + MACHINES)
            for h, date, msg in hashes:
                row = [h, date, msg] + [hash_map.get(h, {}).get(m, "") for m in MACHINES]
                writer.writerow(row)

        # Fancy Plot
        plt.figure(figsize=(14, 6), dpi=200)
        styles = ['o-', 's--', '^-', 'd:', 'x-.', 'v--', '*-', 'p:']
        for i, machine in enumerate(MACHINES):
            y = [hash_map.get(h, {}).get(machine, None) for h, _, _ in hashes]
            if any(y):
                anomalies = detect_anomalies(y)
                plt.plot([h for h, _, _ in hashes], y, styles[i % len(styles)],
                         label=machine, linewidth=2, markersize=6)
                for idx in anomalies:
                    plt.plot(hashes[idx][0], y[idx], 'ro', markersize=8)

        plt.title(f"{ylabel} for {case}", fontsize=16)
        plt.xlabel("Commit Hash", fontsize=14)
        plt.ylabel(ylabel, fontsize=14)
        plt.xticks(rotation=45, fontsize=10)
        plt.yticks(fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend(fontsize=12)
        plt.tight_layout()
        png_path = csv_path.replace(".csv", ".png")
        plt.savefig(png_path)
        plt.close()

def write_summary(app_name, core_matrix, mem_matrix, hashes):
    path = os.path.join(RESULTS_DIR, "summary", f"{app_name}_summary.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(f"# Summary for {app_name}\n\n")
        for case in sorted(core_matrix.keys()):
            f.write(f"## {case}\n")
            core_vals = [core_matrix[case].get(h[0], {}).get(m) for h in hashes for m in MACHINES]
            mem_vals = [mem_matrix[case].get(h[0], {}).get(m) for h in hashes for m in MACHINES]
            core_anoms = len(detect_anomalies(core_vals))
            mem_anoms = len(detect_anomalies(mem_vals))
            f.write(f"- Core hour anomalies: {core_anoms}\n")
            f.write(f"- Memory anomalies: {mem_anoms}\n")
            f.write(f"- Machines: {', '.join(sorted(core_matrix[case].get(hashes[-1][0], {}).keys()))}\n\n")

def process_app_yaml(yaml_file, hashes):
    app_name = os.path.splitext(os.path.basename(yaml_file))[0]
    print(f"\n🔍 Processing app: {app_name}")
    case_map = load_tests_from_yaml(yaml_file)
    core_matrix, mem_matrix = collect_metrics(hashes, case_map)

    walltime_dir = os.path.join(RESULTS_DIR, "walltime", app_name)
    memsize_dir = os.path.join(RESULTS_DIR, "memsize", app_name)

    write_csv_and_plot(core_matrix, hashes, walltime_dir, "", "Core Hours (minutes)")
    write_csv_and_plot(mem_matrix, hashes, memsize_dir, "_memory", "Max Memory (MB)")
    write_summary(app_name, core_matrix, mem_matrix, hashes)

if __name__ == "__main__":
    hashes = get_recent_hashes()
    yaml_files = [os.path.join(BY_APP_DIR, f) for f in os.listdir(BY_APP_DIR) if f.endswith(".yaml")]
    for yaml_file in yaml_files:
        process_app_yaml(yaml_file, hashes)
    print(f"\n✅ All results saved to results/by_app/")

    # Clean up cloned repo
    if os.path.exists(UFS_REPO):
        print(f"🧹 Removing cloned repo: {UFS_REPO}")
        subprocess.run(["rm", "-rf", UFS_REPO])
