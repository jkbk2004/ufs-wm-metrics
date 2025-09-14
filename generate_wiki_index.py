import os
import datetime

# --- CONFIG ---
PLOT_DIR = "."  # Adjust if plots are in a subfolder
OUTPUT_MD = "core_mem_index.md"
PLOT_PREFIX = "core_mem_plot_"
PLOT_SUFFIX = ".png"
REPO_URL = "https://github.com/ufs-community/ufs-weather-model/commit/"

def find_plot_files():
    return sorted([
        f for f in os.listdir(PLOT_DIR)
        if f.startswith(PLOT_PREFIX) and f.endswith(PLOT_SUFFIX)
    ])

def extract_hash(filename):
    return filename[len(PLOT_PREFIX):-len(PLOT_SUFFIX)]

def build_index_md(plot_files):
    lines = []
    lines.append("# 🧠 Core Memory Plot Index\n")
    lines.append(f"_Last updated: {datetime.datetime.now().isoformat()}_\n")

    for fname in plot_files:
        commit_hash = extract_hash(fname)
        short_hash = commit_hash[:7]
        commit_link = f"{REPO_URL}{commit_hash}"
        lines.append(f"### Commit [`{short_hash}`]({commit_link})")
        lines.append(f"![Plot for {short_hash}]({fname})\n")

    return "\n".join(lines)

def write_index(md_text, output_file=OUTPUT_MD):
    with open(output_file, "w") as f:
        f.write(md_text)
    print(f"[INFO] Wiki index written to {output_file}")

if __name__ == "__main__":
    plots = find_plot_files()
    if not plots:
        print("[INFO] No plots found. Skipping index generation.")
    else:
        md = build_index_md(plots)
        write_index(md)
