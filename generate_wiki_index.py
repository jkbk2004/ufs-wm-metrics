import os

def generate_index(root_dir="results/by_app", wiki_out="wiki/Regression-Metrics-by-App.md"):
    """
    Generates a Markdown index page linking to all PNGs under walltime and memsize.

    Args:
        root_dir (str): Path to results directory containing metric subfolders
        wiki_out (str): Path to output Markdown file in Wiki repo
    """
    sections = []
    for metric in ["walltime", "memsize"]:
        metric_dir = os.path.join(root_dir, metric)
        if not os.path.isdir(metric_dir):
            continue

        entries = []
        for fname in sorted(os.listdir(metric_dir)):
            if fname.endswith(".png"):
                app_name = os.path.splitext(fname)[0]
                rel_path = f"regression_metrics/by_app/{metric}/{fname}"
                entries.append(f"- **{app_name}**: ![]({rel_path})")

        if entries:
            sections.append(f"### 📈 {metric.capitalize()}\n" + "\n".join(entries))

    with open(wiki_out, "w") as f:
        f.write("# 📊 Regression Metrics by App\n\n")
        f.write("This page is auto-generated from the latest regression results.\n\n")
        f.write("\n\n".join(sections))
        f.write("\n")

if __name__ == "__main__":
    generate_index()
