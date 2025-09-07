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

import os
import re
import yaml
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict
import subprocess

def get_recent_hashes():
    """
    Retrieves recent commit hashes from the 'develop' branch of the UFS repository.

    Returns:
        list of tuples: Each tuple contains (commit_hash, commit_date, commit_message).
    """
    cmd = ["git", "log", "--pretty=format:%H|%cd|%s", "--date=short", "-n", "20", "origin/develop"]
    output = subprocess.check_output(cmd, text=True)
    hashes = []
    for line in output.strip().split("\n"):
        parts = line.split("|")
        if len(parts) == 3:
            hashes.append((parts[0], parts[1], parts[2]))
    return hashes

def normalize_test_name(name):
    """
    Normalizes test names by removing compiler suffixes.

    Args:
        name (str): Original test name.

    Returns:
        str: Normalized test name.
    """
    return re.sub(r"_(intel|gnu|pgi|nvhpc)$", "", name)

def parse_core_hour(line):
    """
    Parses core hour usage from a log line.

    Args:
        line (str): Log line containing core hour info.

    Returns:
        int or None: Core hour in minutes, or None if not found.
    """
    match = re.search(r"Total wall time: (\d+)m", line)
    return int(match.group(1)) if match else None

def parse_memory_mb(line):
    """
    Parses memory usage from a log line.

    Args:
        line (str): Log line containing memory info.

    Returns:
        int or None: Memory usage in MB, or None if not found.
    """
    match = re.search(r"Max Memory: (\d+) MB", line)
    return int(match.group(1)) if match else None

def load_tests_from_yaml(yaml_path):
    """
    Loads test cases and machine mappings from a YAML file.

    Args:
        yaml_path (str): Path to the YAML config.

    Returns:
        dict: Mapping of normalized test names to sets of machines.
    """
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    case_map = defaultdict(set)
    for machine, tests in data.items():
        for test in tests:
            case_map[normalize_test_name(test)].add(machine)
    return case_map

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
    for commit_hash, _, _ in hashes:
        for test_name, machines in case_map.items():
            for machine in machines:
                log_path = f"logs/{commit_hash}/{machine}/{test_name}.log"
                if not os.path.exists(log_path):
                    continue
                with open(log_path) as f:
                    for line in f:
                        core = parse_core_hour(line)
                        mem = parse_memory_mb(line)
                        if core is not None:
                            core_matrix[test_name][commit_hash][machine] = core
                        if mem is not None:
                            mem_matrix[test_name][commit_hash][machine] = mem
    return core_matrix, mem_matrix

def detect_anomalies(values):
    """
    Detects statistical anomalies in a list of numeric values.

    Args:
        values (list): List of numeric values.

    Returns:
        set: Indices of values that deviate >2 standard deviations from median.
    """
    import numpy as np
    if len(values) < 3:
        return set()
    median = np.median(values)
    std = np.std(values)
    return {i for i, v in enumerate(values) if abs(v - median) > 2 * std}

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
    for test_name, commits in matrix.items():
        csv_path = os.path.join(out_dir, f"{test_name}{suffix}.csv")
        with open(csv_path, "w") as f:
            f.write("commit,date," + ",".join(sorted(next(iter(commits.values())).keys())) + "\n")
            for commit_hash, date, _ in hashes:
                f.write(f"{commit_hash},{date}")
                for machine in sorted(next(iter(commits.values())).keys()):
                    val = commits.get(commit_hash, {}).get(machine, "")
                    f.write(f",{val}")
                f.write("\n")

        # Plotting
        for machine in sorted(next(iter(commits.values())).keys()):
            x = []
            y = []
            for commit_hash, date, _ in hashes:
                val = commits.get(commit_hash, {}).get(machine)
                if val is not None:
                    x.append(date)
                    y.append(val)
            if not y:
                continue
            plt.figure(figsize=(10, 4))
            plt.plot(x, y, marker="o", label=machine)
            anomalies = detect_anomalies(y)
            for i in anomalies:
                plt.plot(x[i], y[i], "ro")
            plt.title(f"{test_name} {suffix} on {machine}")
            plt.ylabel(ylabel)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.legend()
            plot_path = os.path.join(out_dir, f"{test_name}_{machine}{suffix}.png")
            plt.savefig(plot_path)
            plt.close()

def write_summary(app_name, core_matrix, mem_matrix, hashes):
    """
    Writes a Markdown summary of anomalies and machine coverage.

    Args:
        app_name (str): Name of the application.
        core_matrix (dict): Core hour metrics.
        mem_matrix (dict): Memory metrics.
        hashes (list): Commit metadata.
    """
    summary_path = f"results/by_app/{app_name}/summary.md"
    with open(summary_path, "w") as f:
        f.write(f"# Summary for {app_name}\n\n")
        f.write(f"Commits analyzed: {len(hashes)}\n\n")
        for test_name in core_matrix:
            f.write(f"## {test_name}\n")
            for matrix, label in [(core_matrix, "Core Hour"), (mem_matrix, "Memory")]:
                f.write(f"### {label}\n")
                for machine in sorted(next(iter(matrix[test_name].values())).keys()):
                    values = []
                    for commit_hash, _, _ in hashes:
                        val = matrix[test_name].get(commit_hash, {}).get(machine)
                        if val is not None:
                            values.append(val)
                    anomalies = detect_anomalies(values)
                    f.write(f"- {machine}: {len(anomalies)} anomalies\n")

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
    case_map = load_tests_from_yaml(yaml_file)
    core_matrix, mem_matrix = collect_metrics(hashes, case_map)
    out_dir = f"results/by_app/{app_name}"
    write_csv_and_plot(core_matrix, hashes, out_dir, suffix="_core", ylabel="Core Hour (min)")
    write_csv_and_plot(mem_matrix, hashes, out_dir, suffix="_mem", ylabel="Memory (MB)")
    write_summary(app_name, core_matrix, mem_matrix, hashes)

if __name__ == "__main__":
    hashes = get_recent_hashes()
    for yaml_file in sorted(os.listdir("configs/by_app")):
        if yaml_file.endswith(".yaml"):
            process_app_yaml(os.path.join("configs/by_app", yaml_file), hashes)

    print(f"\n✅ All results saved to results/by_app/")

    # Clean up cloned repo
    if os.path.exists(UFS_REPO):
        print(f"🧹 Removing cloned repo: {UFS_REPO}")
        subprocess.run(["rm", "-rf", UFS_REPO])
