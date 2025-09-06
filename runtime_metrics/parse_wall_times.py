import os
import json
import csv
from datetime import datetime
from statistics import median
from collections import defaultdict

def parse_wall_time(line):
    """
    Extracts wall time in minutes from a log line like: [14:12, 12:44]
    """
    if "[" in line and "]" in line:
        try:
            time_block = line.split("[")[1].split("]")[0]
            time_str = time_block.split(",")[0].strip()  # e.g. "14:12"
            h, m = map(int, time_str.split(":"))
            return h * 60 + m
        except (IndexError, ValueError):
            return None
    return None

def extract_baseline_dates(conf_path="bl_date.conf"):
    dates = []
    if not os.path.exists(conf_path):
        print(f"⚠️ Baseline config not found: {conf_path}")
        return dates

    with open(conf_path) as f:
        for line in f:
            if "export BL_DATE=" in line:
                date_str = line.strip().split("=")[-1]
                try:
                    dates.append(datetime.strptime(date_str, "%Y%m%d").date())
                except ValueError:
                    continue
    return sorted(set(dates))

def extract_wall_times(log_dir=".", conf_path="bl_date.conf"):
    raw_data = defaultdict(list)

    for fname in sorted(os.listdir(log_dir)):
        if not fname.startswith("RegressionTests_") or not fname.endswith(".log"):
            continue

        path = os.path.join(log_dir, fname)
        date_match = fname.split("_")[-1].replace(".log", "")
        try:
            log_date = datetime.strptime(date_match, "%Y%m%d").date()
        except ValueError:
            log_date = datetime.fromtimestamp(os.path.getmtime(path)).date()

        with open(path) as f:
            for line in f:
                if "PASS -- TEST" in line and "[" in line:
                    try:
                        test_name = line.split("TEST '")[1].split("'")[0]
                        wall_time = parse_wall_time(line)
                        if wall_time:
                            raw_data[test_name].append((log_date, wall_time))
                    except IndexError:
                        continue

    final_data = defaultdict(list)
    for test_name, entries in raw_data.items():
        times = [t for _, t in entries]
        med = median(times)
        for date, time in entries:
            anomaly = None
            if time > 1.5 * med:
                anomaly = "spike"
            elif time < 0.5 * med:
                anomaly = "drop"
            final_data[test_name].append({
                "date": date.isoformat(),
                "wall_time": time,
                "anomaly": anomaly
            })

    with open("wall_time_data.json", "w") as jf:
        json.dump(final_data, jf, indent=2)

    with open("wall_time_data.csv", "w", newline="") as cf:
        writer = csv.writer(cf)
        writer.writerow(["Test", "Date", "WallTime", "Anomaly"])
        for test_name, entries in final_data.items():
            for entry in entries:
                writer.writerow([test_name, entry["date"], entry["wall_time"], entry["anomaly"] or ""])

    baseline_dates = extract_baseline_dates(conf_path)
    return final_data, baseline_dates
