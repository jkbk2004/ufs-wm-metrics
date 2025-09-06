import os
import re
import json
import csv
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import datetime
from collections import OrderedDict

LOG_DIR = "tests/logs"  # Path to logs inside ufs-weather-model
NUM_COMMITS = 10        # Number of commits to process

def get_recent_hashes():
    os.system("git -C ufs-weather-model fetch origin develop")
    hashes = os.popen("git -C ufs-weather-model log origin/develop -n {} --pretty=format:'%h'".format(NUM_COMMITS)).read().splitlines()
    return [h.strip("'") for h in hashes]

def parse_compile_time(log_path):
    with open(log_path) as f:
        for line in f:
            if "COMPILE" in line and "[" in line and "]" in line:
                try:
                    time_block = line.split("[")[1].split("]")[0]
                    time_str = time_block.split(",")[0].strip()
                    h, m = map(int, time_str.split(":"))
                    return h * 60 + m
                except Exception:
                    continue
    return None

def collect_compile_times(hashes):
    data = OrderedDict()
    for h in hashes:
        log_file = os.path.join(LOG_DIR, f"RegressionTests_{h}.log")
        if os.path.exists(log_file):
            wall_time = parse_compile_time(log_file)
            if wall_time:
                data[h] = wall_time
    return data

def export_csv(data):
    with open("compile_wall_time.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Commit", "WallTime"])
        for h, t in data.items():
            writer.writerow([h, t])

def plot_static(data):
    plt.figure(figsize=(12, 6))
    plt.plot(list(data.keys()), list(data.values()), marker="o", color="blue")
    plt.xticks(rotation=45)
    plt.title("COMPILE Wall Time Over Last 10 Commits")
    plt.xlabel("Commit Hash")
    plt.ylabel("Wall Time (minutes)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("compile_wall_time.png")
    print("✅ Static plot saved to compile_wall_time.png")

def plot_interactive(data):
    import pandas as pd
    df = pd.DataFrame({"Commit": list(data.keys()), "WallTime": list(data.values())})
    fig = px.line(df, x="Commit", y="WallTime", title="COMPILE Wall Time Over Last 10 Commits", markers=True)
    fig.write_html("compile_wall_time.html")
    print("✅ Interactive plot saved to compile_wall_time.html")

if __name__ == "__main__":
    hashes = get_recent_hashes()
    data = collect_compile_times(hashes)
    export_csv(data)
    plot_static(data)
    plot_interactive(data)
