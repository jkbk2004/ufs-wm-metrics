import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd

def plot_static(data, baseline_dates, output="wall_time_timeseries.png"):
    plt.figure(figsize=(14, 7))
    for test, entries in data.items():
        dates = [e["date"] for e in entries]
        times = [e["wall_time"] for e in entries]
        plt.plot(dates, times, label=test)

        for e in entries:
            if e["anomaly"] == "spike":
                plt.plot(e["date"], e["wall_time"], "r^", markersize=6)
            elif e["anomaly"] == "drop":
                plt.plot(e["date"], e["wall_time"], "go", markersize=6)

    for bdate in baseline_dates:
        plt.axvline(bdate.isoformat(), color="gray", linestyle="--", alpha=0.5)
        plt.text(bdate.isoformat(), plt.ylim()[1]*0.95, f"BL {bdate}", rotation=90, fontsize=8)

    plt.title("UFS Regression Test Wall Times Over Time")
    plt.xlabel("Date")
    plt.ylabel("Wall Time (minutes)")
    plt.legend(loc="upper left", fontsize=7)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output)
    print(f"✅ Static plot saved to {output}")

def plot_interactive(data, baseline_dates, output="wall_time_timeseries.html"):
    rows = []
    for test, entries in data.items():
        for e in entries:
            rows.append({
                "Test": test,
                "Date": e["date"],
                "WallTime": e["wall_time"],
                "Anomaly": e["anomaly"] or ""
            })
    df = pd.DataFrame(rows)

    fig = px.line(df, x="Date", y="WallTime", color="Test", title="UFS Wall Time Trends", hover_data=["Anomaly"])
    for bdate in baseline_dates:
        fig.add_vline(x=bdate.isoformat(), line_dash="dash", line_color="gray", annotation_text=f"BL {bdate}", annotation_position="top left")

    fig.write_html(output)
    print(f"✅ Interactive plot saved to {output}")
