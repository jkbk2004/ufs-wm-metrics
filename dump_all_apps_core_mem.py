"""
dump_all_apps_core_mem.py

Automated regression metrics pipeline for UFS workflow testing.

This script clones the required UFS repositories, parses regression test logs across multiple machines,
extracts core hour and memory usage for each test case defined in all YAML configs under `by_app/`,
flags anomalies, and generates CSVs, plots, and Markdown summaries.

Features:
- Clones `ufs-weather-model` and `ufs-wm-metrics` if not present
- Scans all test definitions in `ufs-wm-metrics/tests-yamls/configs/by_app/*.yaml`
- Parses logs from machines: orion, hera, gaeac6, hercules, derecho, ursa, wcoss2, acorn
- Extracts:
    - Core hour usage (second time in brackets)
    - Max memory usage (value in parentheses)
- Flags anomalies using rolling median and standard deviation
- Saves results to:
    - results/by_app/walltime/<app>/<test>.csv + .png
    - results/by_app/memsize/<app>/<test>_memory.csv + .png
    - results/by_app/summary/<app>_summary.md

Intended for use in CI/CD pipelines or GitHub Actions to automate performance tracking and regression detection.

Author: Jong Kim
License: MIT
"""

import os
import subprocess
import yaml
import csv
import matplotlib.pyplot as plt
from collections import defaultdict
import statistics

# Clone repos if missing
if not os.path.exists("ufs-weather-model"):
    subprocess.run(["git", "clone", "https://github.com/ufs-community/ufs-weather-model.git"])
if not os.path.exists("ufs-wm-metrics"):
    subprocess.run(["git", "clone", "https://github.com/ufs-community/ufs-wm-metrics.git"])

# Config
UFS_REPO = "ufs-weather-model"
BY_APP_DIR = "ufs-wm-metrics/tests-yamls/configs/by_app"
RESULTS_DIR = "results/by_app"
MACHINES = ["orion", "hera", "gaeac6", "hercules", "derecho", "ursa", "wcoss2", "acorn"]
NUM_COMMITS = 50

def get_recent_hashes():
    """
    Fetches the latest commit hashes from the UFS repository.

    Returns:
        List of tuples: Each tuple contains (commit hash, date, commit message).
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
    Normalizes test case names by removing known compiler suffixes.

    Args:
        name (str): Raw test name from log file.

    Returns:
        str: Normalized test name.
    """
    for suffix in ["_intel", "_gnu", "_pgi", "_nvhpc"]:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name

def parse_core_hour(line):
    """
    Extracts core hour usage from a log line.

    Args:
        line (str): A line from the regression test log.

    Returns:
        int or None: Core hour usage in minutes, or None if parsing fails.
    """
    try:
        time_block = line.split("[")[1].split("]")[0]
        core_str = time_block.split(",")[1].strip()
        h, m = map(int, core_str.split(":"))
        return h * 60 + m
    except:
        return None

def parse_memory_mb(line):
    """
    Extracts maximum memory usage from a log line.

    Args:
        line (str): A line from the regression test log.

    Returns:
        int or None: Memory usage in MB, or None if parsing fails.
    """
    try:
        mem_str = line.split("(")[1].split("MB")[0].strip()
        return int(mem_str)
    except:
        return None

def load_tests_from_yaml(yaml_path):
    """
    Loads test case definitions from a YAML config file.

    Args:
        yaml_path (str): Path to the YAML file.

    Returns:
        dict: Mapping of test names to supported machines.
    """
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
    """
    Parses logs across commits and machines to extract core hour and memory usage.

    Args:
        hashes (list): List of commit metadata tuples.
        case_map (dict): Mapping of test names to machines.

    Returns:
        tuple: Two nested dictionaries for core hour and memory metrics.
    """
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
    """
    Flags anomalies in a list of numeric values using median and standard deviation.

    Args:
        values (list): List of numeric values (may include None).

    Returns:
        set: Indices of values considered anomalous.
    """
    clean = [v for v in values if isinstance(v, (int, float))]
    if len(clean) < 5:
        return set()
    median = statistics.median(clean)
    stdev = statistics.stdev(clean)
    return {i for i, v in enumerate(values) if isinstance(v, (int, float)) and abs(v - median) > 2 * stdev}

def write_csv_and_plot(matrix, hashes, out_dir, suffix="", ylabel=""):
    """
    Writes CSV files and generates plots for each test case.

    Args:
        matrix (dict): Nested dictionary of metrics per test case.
        hashes (list): List of commit metadata tuples.
        out_dir (str): Output directory for CSVs and plots.
        suffix (str): Optional suffix for filenames (e.g. "_memory").
        ylabel (str): Label for the Y-axis in plots.
    """
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
