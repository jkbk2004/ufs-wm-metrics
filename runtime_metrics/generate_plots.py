from parse_wall_times import extract_wall_times
from plot_wall_times import plot_static, plot_interactive

data, baseline_dates = extract_wall_times(log_dir=".", conf_path="bl_date.conf")
plot_static(data, baseline_dates)
plot_interactive(data, baseline_dates)
