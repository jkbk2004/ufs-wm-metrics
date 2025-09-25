import os
import csv
import numpy as np
from collections import defaultdict

# Accumulator: {(machine, compiler): [row_dicts]}
stats_by_machine_compiler = defaultdict(list)

def extract_compiler(case_name, compilers=["intel", "gnu", "intellvm", "intelllvm"]):
    return next((c for c in compilers if case_name.endswith(c)), "unknown")

def accumulate_case_stats(machine, case_name, walltimes, memsizes):
    compiler = extract_compiler(case_name)
    stats = {
        "case_name": case_name,
        "walltime_mean": round(np.mean(walltimes), 3),
        "walltime_min": round(np.min(walltimes), 3),
        "walltime_max": round(np.max(walltimes), 3),
        "walltime_std": round(np.std(walltimes), 3),
        "memsize_mean": round(np.mean(memsizes), 3),
        "memsize_min": round(np.min(memsizes), 3),
        "memsize_max": round(np.max(memsizes), 3),
        "memsize_std": round(np.std(memsizes), 3),
    }
    stats_by_machine_compiler[(machine, compiler)].append(stats)

def write_all_stats_csv(outdir="results/stats"):
    os.makedirs(outdir, exist_ok=True)
    for (machine, compiler), rows in stats_by_machine_compiler.items():
        csv_path = os.path.join(outdir, f"{machine}_{compiler}_stats.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"📄 Wrote {csv_path} with {len(rows)} cases")
