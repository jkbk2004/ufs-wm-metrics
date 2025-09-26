import os
import shutil

# Paths
WIKI_PATH = "wiki/Regression-Metrics-by-App.md"
WALLTIME_SRC = "results/by_app/walltime"
STATS_SRC = "results/stats"
WALLTIME_DST = "wiki/walltime"
STATS_DST = "wiki/stats"

def sync_walltime_images():
    for app in os.listdir(WALLTIME_SRC):
        for compiler in os.listdir(os.path.join(WALLTIME_SRC, app)):
            src_dir = os.path.join(WALLTIME_SRC, app, compiler)
            dst_dir = os.path.join(WALLTIME_DST, app, compiler)
            if os.path.isdir(src_dir):
                os.makedirs(dst_dir, exist_ok=True)
                for fname in os.listdir(src_dir):
                    if fname.endswith(".png"):
                        shutil.copyfile(os.path.join(src_dir, fname), os.path.join(dst_dir, fname))

def sync_stats_csvs():
    os.makedirs(STATS_DST, exist_ok=True)
    for fname in os.listdir(STATS_SRC):
        if fname.endswith(".csv"):
            shutil.copyfile(os.path.join(STATS_SRC, fname), os.path.join(STATS_DST, fname))

def get_walltime_links():
    links = []
    for app in sorted(os.listdir(WALLTIME_DST)):
        app_path = os.path.join(WALLTIME_DST, app)
        for compiler in sorted(os.listdir(app_path)):
            rel_path = f"walltime/{app}/{compiler}"
            links.append((app, compiler, rel_path))
    return links

def get_stats_links():
    links = []
    for fname in sorted(os.listdir(STATS_DST)):
        if fname.endswith(".csv"):
            parts = fname.replace(".csv", "").split("_")
            if len(parts) >= 2:
                test_name = parts[0]
                compiler = "_".join(parts[1:])
                rel_path = f"stats/{fname}"
                links.append((test_name, compiler, rel_path))
    return links

def generate_wiki():
    sync_walltime_images()
    sync_stats_csvs()

    lines = []
    lines.append("## 🧮 Regression Metrics by App\n")
    lines.append("This page summarizes performance metrics collected across commits, machines, and compilers.\n")
    lines.append("---\n")

    # Walltime section
    lines.append("### 📊 Walltime Results\n")
    lines.append("Organized by app and compiler:\n")
    walltime_links = get_walltime_links()
    apps = sorted(set(app for app, _, _ in walltime_links))
    for app in apps:
        lines.append(f"- **{app.upper()}**")
        for a, compiler, rel_path in walltime_links:
            if a == app:
                lines.append(f"  - [{compiler.upper()}]({rel_path})")

    # Stats section
    lines.append("\n### 📈 Summary Statistics\n")
    lines.append("Grouped by test name and compiler. Each file includes machine-level stats across hashes:\n")
    for test_name, compiler, rel_path in get_stats_links():
        label = f"{test_name.upper()} {compiler.upper()} Stats"
        lines.append(f"- [{label}]({rel_path})")

    os.makedirs(os.path.dirname(WIKI_PATH), exist_ok=True)
    with open(WIKI_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"[UPDATE] Wiki index written to {WIKI_PATH}")

if __name__ == "__main__":
    generate_wiki()
