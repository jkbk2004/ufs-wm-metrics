import argparse
import sys
from trigger import get_latest_hash, has_new_commit, log_trigger_event
from plot_core_mem import dump_core_mem_plot

def parse_args():
    parser = argparse.ArgumentParser(description="Dump core memory usage plots.")
    parser.add_argument("--input", type=str, help="Path to regression log file")
    parser.add_argument("--config", type=str, help="Optional config file")
    parser.add_argument("--force", action="store_true", help="Force plot even if no new commit")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    latest = get_latest_hash()

    if args.force or (latest and has_new_commit(latest)):
        print(f"[INFO] Triggering plot for commit: {latest}")
        log_trigger_event(latest)
        dump_core_mem_plot(latest, args)
    else:
        print("[INFO] No new commit. Skipping plot generation.")
        sys.exit(0)
