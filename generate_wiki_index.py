import os
from trigger import get_latest_hash, has_new_commit, log_trigger_event

def generate_index(root_dir="wiki/regression_metrics/by_app", wiki_out="wiki/Regression-Metrics-by-App.md"):
    os.makedirs(os.path.dirname(wiki_out), exist_ok=True)

    sections = []
    for metric in ["walltime", "memsize"]:
        metric_dir = os.path.join(root_dir, metric)
        print(f"Scanning: {metric_dir}")

        if not os.path.isdir(metric_dir):
            print(f"Directory not found: {metric_dir}")
            continue

        app_sections = []
        for app_name in sorted(os.listdir(metric_dir)):
            app_dir = os.path.join(metric_dir, app_name)
            if not os.path.isdir(app_dir):
                continue

            pngs = [f for f in sorted(os.listdir(app_dir)) if f.endswith(".png")]
            if not pngs:
                continue

            images_md = "\n".join([f"![](regression_metrics/by_app/{metric}/{app_name}/{f})" for f in pngs])
            app_md = f"""<details>
<summary><strong>{app_name}</strong></summary>

{images_md}

</details>"""
            app_sections.append(app_md)

        if app_sections:
            sections.append(f"### 📈 {metric.capitalize()}\n" + "\n\n".join(app_sections))

    with open(wiki_out, "w") as f:
        f.write("# 📊 Regression Metrics by App\n\n")
        f.write("This page is auto-generated from the latest regression results.\n\n")
        if sections:
            f.write("\n\n".join(sections))
        else:
            f.write("_No plots found in Wiki repo._\n")

if __name__ == "__main__":
    latest = get_latest_hash()
    if latest and has_new_commit(latest):
        generate_index()
