import os

WIKI_PATH = "wiki/Regression-Metrics-by-App.md"
WALLTIME_ROOT = "results/by_app/walltime"
STATS_ROOT = "results/by_app/stats"

def get_walltime_links():
    """
    Scans results/by_app/walltime and returns a list of (app, compiler, relative_path)
    """
    links = []
    for app in sorted(os.listdir(WALLTIME_ROOT)):
        app_path = os.path.join(WALLTIME_ROOT, app)
        if not os.path.isdir(app_path):
            continue
        for compiler in sorted(os.listdir(app_path)):
            compiler_path = os.path.join(app_path, compiler)
            if os.path.isdir(compiler_path):
                rel_path = f"../{compiler_path}"
                links.append((app, compiler, rel_path))
    return links

def get_stats_links():
    """
    Scans results/by_app/stats and returns a list of (test_name, compiler, relative_path)
    """
    links = []
    for fname in sorted(os.listdir(STATS_ROOT)):
        if fname.endswith(".csv"):
            parts = fname.replace(".csv", "").split("_")
            if len(parts) >= 2:
                test_name = parts[0]
                compiler = "_".join(parts[1:])
                rel_path = f"../{STATS_ROOT}/{fname}"
                links.append((test_name, compiler, rel_path))
    return links

def generate_wiki():
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

    # Write to file
    os.makedirs(os.path.dirname(WIKI_PATH), exist_ok=True)
    with open(WIKI_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"[UPDATE] Wiki index written to {WIKI_PATH}")

if __name__ == "__main__":
    generate_wiki()
