import matplotlib.pyplot as plt

def dump_core_mem_plot(commit_hash, args):
    print("[INFO] Running core memory plot dump...")

    # Replace with actual log parsing using args.input or args.config
    run_ids = ["run1", "run2", "run3"]
    memory_usage = [1200, 1350, 1280]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(run_ids, memory_usage, marker='o', linestyle='-')
    ax.set_title("Core Memory Usage per Run")
    ax.set_xlabel("Run ID")
    ax.set_ylabel("Memory (MB)")
    ax.grid(True)

    filename = f"core_mem_plot_{commit_hash[:7]}.png"
    plt.tight_layout()
    plt.savefig(filename)
    print(f"[INFO] Plot saved as {filename}")
