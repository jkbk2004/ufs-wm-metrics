import os

def generate_index(root_dir="wiki/regression_metrics/by_app", wiki_out="wiki/Regression-Metrics-by-App.md"):
    """
    Recursively generates a Markdown index linking to all PNGs under walltime and memsize inside the Wiki repo.
    """
    os.makedirs(os.path.dirname(wiki_out), exist_ok=True)

    sections = []
    for metric in ["walltime", "memsize"]:
        metric_dir = os.path.join(root_dir, metric)
        print(f"Scanning: {metric_dir}")

        if not os.path.isdir(metric_dir):
            print(f"Directory not found: {metric_dir}")
            continue

        entries = []
        for root, _, files in os.walk(metric_dir):
            for fname in sorted(files):
                if fname.endswith(".png"):
                    app_name = os.path.splitext(fname)[0]
                    rel_path = os.path.relpath(os.path.join(root, fname), start="wiki")
                    entries.append(f"- **{app_name}**: ![]({rel_path})")

        print(f"Found {len(entries)} PNGs in {metric}")
        if entries:
            section_md = f"### 📈 {metric.capitalize()}\n" + "\n".join(entries)
            sections.append(section_md)

    with open(wiki_out, "w") as f:
        f.write("# 📊 Regression Metrics by App\n\n")
        f.write("This page is auto-generated from the latest regression results.\n\n")
        if sections:
            f.write("\n\n".join(sections))
        else:
            f.write("_No plots found in Wiki repo._\n")

if __name__ == "__main__":
    generate_index()
