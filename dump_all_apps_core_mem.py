"""
dump_all_apps_core_mem.py

Analyzes core hour and memory usage across recent commits for multiple UFS workflow applications.

This script performs the following:
- Retrieves recent commit metadata from the local Git repository
- Loads test configurations from app-specific YAML files
- Parses log files to extract core hour and memory metrics per test, machine, and commit
- Detects statistical anomalies in resource usage
- Outputs CSV files and annotated plots for each test and metric
- Generates Markdown summaries highlighting anomalies and machine coverage

Directory structure assumptions:
- Log files: logs/<commit>/<machine>/<test>.log
- Configs: configs/by_app/<app>.yaml
- Output: results/by_app/<app>/

Intended for maintainers and contributors seeking reproducible performance tracking across workflow versions.

Author: Jong Kim
"""
# Top of script: clone repos if missing
import os, subprocess
if not os.path.exists("ufs-weather-model"):
    subprocess.run(["git", "clone", "https://github.com/ufs-community/ufs-weather-model.git"])

# Imports
import re
import yaml, csv, matplotlib.pyplot as plt
from collections import defaultdict
import statistics
from trigger import get_latest_hash, has_new_commit, log_trigger_event
from datetime import datetime, timedelta

# Config
UFS_REPO = "ufs-weather-model"
BY_APP_DIR = "tests-yamls/configs/by_app"
RESULTS_DIR = "results/by_app"
MACHINES = ["orion", "hera", "gaeac6", "hercules", "derecho", "ursa", "wcoss2", "acorn"]
NUM_COMMITS = 5
DRIFT_THRESHOLD_DAYS = 7

# === UTILS ===
def get_log_end_datetime(log_path):
    """Parses the 'Ending Date/Time' from the log file, supporting multiple formats."""
    if not os.path.exists(log_path):
        return None

    with open(log_path, "r") as f:
        for line in f:
            # Format 1: YYYYMMDD HH:MM:SS
            match1 = re.search(r"Ending Date/Time:\s*(\d{8})\s+(\d{2}:\d{2}:\d{2})", line)
            if match1:
                date_str = match1.group(1)
                time_str = match1.group(2)
                return datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H:%M:%S")

            # Format 2: YYYY-MM-DD HH:MM:SS
            match2 = re.search(r"Ending Date/Time:\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})", line)
            if match2:
                date_str = match2.group(1)
                time_str = match2.group(2)
                return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")

    return None  # No valid timestamp found

def is_machine_drifting_by_log_timestamp(log_path, hash_date):
    log_datetime = get_log_end_datetime(log_path)
    if log_datetime is None or hash_date is None:
        return True

    age = hash_date - log_datetime
    return age > timedelta(days=DRIFT_THRESHOLD_DAYS)

def get_recent_hashes():
    """
    Retrieves recent commit hashes from the 'develop' branch of the UFS repository.

    Returns:
        list of tuples: Each tuple contains (commit_hash, commit_date, commit_message).
    """
    subprocess.run(["git", "-C", UFS_REPO, "fetch", "origin", "develop"])
    result = subprocess.run(
        ["git", "-C", UFS_REPO, "log", "origin/develop", "-n", str(NUM_COMMITS),
         "--pretty=format:%h|%ad|%s", "--date=short"],
        capture_output=True, text=True
    )
    return [line.strip().split("|") for line in result.stdout.strip().splitlines()]

def normalize_test_name(name):
    """
    Normalizes test names by removing compiler suffixes.

    Args:
        name (str): Original test name.

    Returns:
        str: Normalized test name.
    """    
    for suffix in ["_intel", "_gnu", "_pgi", "_nvhpc"]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name

def parse_core_hour(line):
    """
    Parses core hour usage from a log line.

    Args:
        line (str): Log line containing core hour info.

    Returns:
        int or None: Core hour in seconds, or None if not found.
    """    
    try:
        time_block = line.split("[")[1].split("]")[0]
        core_str = time_block.split(",")[1].strip()
        mm, ss = map(int, core_str.split(":"))
        return mm * 60 + ss
    except:
        return None

def parse_memory_mb(line):
    """
    Parses memory usage from a log line.

    Args:
        line (str): Log line containing memory info.

    Returns:
        int or None: Memory usage in MB, or None if not found.
    """    
    try:
        mem_str = line.split("(")[1].split("MB")[0].strip()
        return int(mem_str)
    except:
        return None

def load_tests_from_yaml(yaml_path):
    """
    Loads test cases and machine mappings from a YAML file.

    Args:
        yaml_path (str): Path to the YAML config.

    Returns:
        dict: Mapping of normalized test names to sets of machines.
    """    
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    case_map = defaultdict(set)
    for app_name, app_config in config.items():
        for entry in app_config.get("tests", []):
            if isinstance(entry, dict):
                for test_name in entry.keys():
                    for machine in MACHINES:
                        compiler = app_config.get("build", {}).get("compiler", "unknown")
                        test_id = f"{test_name}_{compiler}"
                        case_map[test_id].add(machine)
    return case_map

def sanitize_log_line(line):
    """
    Sanitize regression log line to enforce:
    - TEST name wrapped in single quotes
    - Memory value capped to 7 digits and scaled down if necessary

    Args:
        line (str): Raw log line from regression output

    Returns:
        str: Sanitized log line
    """
    if "PASS -- TEST" not in line or "[" not in line or "(" not in line:
        return line  # Skip irrelevant lines

    # Ensure TEST name is quoted
    if "TEST '" not in line:
        try:
            test_start = line.index("TEST ") + len("TEST ")
            test_end = line.index(" [", test_start)
            test_name = line[test_start:test_end].strip()
            line = line.replace(f"TEST {test_name}", f"TEST '{test_name}'")
        except ValueError:
            pass  # Leave line unchanged if parsing fails

    # Normalize memory value
    try:
        mem_start = line.index("(") + 1
        mem_end = line.index("MB", mem_start)
        mem_str = line[mem_start:mem_end].strip()
        mem_val = int(mem_str)
        if mem_val > 9999999:
            mem_val = mem_val // 1000  # Convert to GB-scale MB
            line = line[:mem_start] + f"{mem_val} " + line[mem_end:]
    except ValueError:
        pass  # Leave memory unchanged if parsing fails

    return line

def collect_metrics(hashes, case_map):
    """
    Collects core hour and memory metrics from logs across commits and machines.

    Args:
        hashes (list): List of commit metadata.
        case_map (dict): Mapping of test names to machines.

    Returns:
        tuple: (core_matrix, mem_matrix) as nested dicts:
               test_name → commit_hash → machine → metric_value
    """    
    core_matrix = defaultdict(lambda: defaultdict(dict))
    mem_matrix = defaultdict(lambda: defaultdict(dict))
    for h, date, msg in hashes:
        #subprocess.run(["git", "-C", UFS_REPO, "stash", "push", "-m", "temp before checkout"])
        subprocess.run(["git", "-C", UFS_REPO, "checkout", h],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        #jkim subprocess.run(["git", "-C", UFS_REPO, "checkout", h])
        #jkim subprocess.run(["git", "-C", UFS_REPO, "checkout", h], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        hash_date = datetime.fromisoformat(date) if isinstance(date, str) else date
        #jkim print(f"\n[HASH] {h} @ {hash_date.date()}")
        for machine in MACHINES:
            log_path = os.path.join(UFS_REPO, "tests", "logs", f"RegressionTests_{machine}.log")
            if not os.path.exists(log_path):
                continue

            if is_machine_drifting_by_log_timestamp(log_path, hash_date):
                print(f"[SKIP] {machine}: log timestamp is older than hash by > {DRIFT_THRESHOLD_DAYS} days → drifting.")
                continue            

            compiler_from_log = None
            with open(log_path) as f:
                for raw_line in f:
                    line = sanitize_log_line(raw_line)
                    if "PASS -- COMPILE" in line or "PASS -- TEST" in line:
                        match = re.search(r"'([^']+)'", line)
                        if match:
                            test_id = match.group(1)
                            parts = test_id.split("_")
                            candidate = parts[-1].lower()
                            if candidate in ["gnu", "intel", "intelllvm"]:
                                compiler_from_log = candidate
                    if "PASS -- TEST" in line and "[" in line and "(" in line:
                        try:
                            raw_name = line.split("TEST '")[1].split("'")[0]
                            normalized = raw_name #normalize_test_name(raw_name)
                            core_hour = parse_core_hour(line)
                            memory_mb = parse_memory_mb(line)
                            #print(raw_name,normalized,log_path,machine)
                            if normalized in case_map and machine in case_map[normalized]:
                                if core_hour:
                                    core_matrix[normalized][h][machine] = core_hour
                                if memory_mb:
                                    mem_matrix[normalized][h][machine] = memory_mb
                        except:
                            continue
    return core_matrix, mem_matrix, compiler_from_log

def detect_anomalies(values):
    """
    Detects statistical anomalies in a list of numeric values.

    Args:
        values (list): List of numeric values.

    Returns:
        set: Indices of values that deviate >2 standard deviations from median.
    """    
    clean = [v for v in values if isinstance(v, (int, float))]
    if len(clean) < 5:
        return set()
    median = statistics.median(clean)
    stdev = statistics.stdev(clean)
    return {i for i, v in enumerate(values) if isinstance(v, (int, float)) and abs(v - median) > 2 * stdev}

def write_csv_and_plot(matrix, hashes, out_dir, suffix="", ylabel=""):
    """
    Writes metrics to CSV and generates anomaly-highlighted plots.

    Args:
        matrix (dict): Nested dict of metrics.
        hashes (list): Commit metadata.
        out_dir (str): Output directory for CSV and plots.
        suffix (str): Optional suffix for filenames.
        ylabel (str): Label for Y-axis in plots.
    """    
    os.makedirs(out_dir, exist_ok=True)
    for case, hash_map in matrix.items():
        print(case)
        csv_path = os.path.join(out_dir, f"{case}{suffix}.csv")

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
        # Ensure left-to-right progression
        plt.gca().invert_xaxis()
        plt.ylabel(ylabel, fontsize=14)
        plt.xticks(rotation=45, fontsize=10)
        plt.yticks(fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend(fontsize=12)
        plt.tight_layout()
        png_path = csv_path.replace(".csv", ".png")
        plt.savefig(png_path)
        plt.close()

def process_app_yaml(yaml_file, hashes):
    """
    Processes a single app YAML file:
    - Loads test cases
    - Extracts metrics
    - Writes CSVs and plots
    - Summarizes anomalies

    Args:
        yaml_file (str): Path to the app-specific YAML config.
        hashes (list): Commit metadata.
    """    
    app_name = os.path.splitext(os.path.basename(yaml_file))[0]
    print(f"\n🔍 Processing app: {app_name}")
    case_map = load_tests_from_yaml(yaml_file)
    core_matrix, mem_matrix, compiler_log = collect_metrics(hashes, case_map)

    walltime_dir = os.path.join(RESULTS_DIR, "walltime", app_name)
    memsize_dir = os.path.join(RESULTS_DIR, "memsize", app_name)

    write_csv_and_plot(core_matrix, hashes, walltime_dir, "", "Core Hours (seconds)")
    write_csv_and_plot(mem_matrix, hashes, memsize_dir, "_memory", "Max Memory (MB)")

if __name__ == "__main__":
    latest = get_latest_hash()
    if latest and has_new_commit(latest):
        log_trigger_event(latest)
        print("# Proceed with plotting or other logic")
    
        hashes = get_recent_hashes()
        yaml_files = [os.path.join(BY_APP_DIR, f) for f in os.listdir(BY_APP_DIR) if f.endswith(".yaml")]
        for yaml_file in yaml_files:
            process_app_yaml(yaml_file, hashes)
        print(f"\n✅ All results saved to results/by_app/")

        # Clean up cloned repo
        if os.path.exists(UFS_REPO):
            print(f"🧹 Removing cloned repo: {UFS_REPO}")
            subprocess.run(["rm", "-rf", UFS_REPO])
