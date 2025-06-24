import os
import subprocess
import re
import csv
from itertools import product
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration ranges (logarithmic doubling)
latency_goals = [x for x in [2 ** i for i in range(0, 1)]]  # 1 to 256 us
read_iops_bandwidth_pairs = [(100000 * 2 ** i, 2 ** i) for i in range(0, 8)]

mountpoint = "/var/lib/scylla/robitza"
output_dir = "iotune_configs"
os.makedirs(output_dir, exist_ok=True)
read_csv_path = os.path.join(output_dir, "iotune_results_read.csv")
write_csv_path = os.path.join(output_dir, "iotune_results_write.csv")
yaml_path = os.path.join(output_dir, "io-properties.yaml")

def run_ioinfo(read_iops, read_bw, write_iops, write_bw, latency, mode):
    yaml_template = f"""
disks:
  - mountpoint: {mountpoint}
    read_iops: {read_iops}
    read_bandwidth: {read_bw}G
    write_iops: {write_iops}
    write_bandwidth: {write_bw}G
"""
    with open(yaml_path, "w") as f:
        f.write(yaml_template)

    cmd = [
        "sudo", "./build/release/seastar/apps/io_tester/ioinfo",
        f"--directory={mountpoint}",
        f"--io-properties-file={yaml_path}",
        f"--io-latency-goal={latency}"
    ]

    try:
        print(f"Running {mode} test with read_iops={read_iops}, read_bw={read_bw}G, write_iops={write_iops}, write_bw={write_bw}G...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        print(f"Standard Error Output:\n{e.stderr}")
        return None

def parse_output(output, latency, iops, bw, rw_mode, metric_mode):
    if output is None:
        return None

    rate_match = re.search(r" rate:\s*(\d+)", output)

    req_size = 512 if metric_mode == "iops" else 131072
    cost_match = re.search(rf"{req_size}:\s*\n\s*read:\s*(\d+)\n\s*write:\s*(\d+)", output)
    if rate_match and cost_match:
        rate = int(rate_match.group(1))
        cost = int(cost_match.group(1)) if rw_mode == "read" else int(cost_match.group(2))
    else:
        print("Could not parse rate or bandwidth cost from output.")
        return None

    req_per_sec = 0 if cost == 0 else rate / cost * 1000
    return [latency, iops, bw, rate, cost, req_per_sec]

def generate_csv(path, rw_mode, metric_mode):
    field_prefix = f"{rw_mode}_"
    with open(path, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["latency_goal", field_prefix + "iops", field_prefix + "bandwidth", "rate", "cost", field_prefix + ("req_per_sec" if metric_mode == "iops" else "bw_per_sec")])

        for latency in latency_goals:
            for iops, bw in read_iops_bandwidth_pairs:
                output = run_ioinfo(
                    iops if rw_mode == "read" else 100000,
                    bw if rw_mode == "read" else 1,
                    1000 if rw_mode == "read" else iops,
                    1 if rw_mode == "read" else bw,
                    latency,
                    rw_mode
                )
                row = parse_output(output, latency, iops, bw, rw_mode, metric_mode)
                if row:
                    writer.writerow(row)

def plot_vs_computed(csv_path, rw_mode, metric_mode):
    df = pd.read_csv(csv_path)
    df = df[df["latency_goal"] == 1]
    print(df)

    iops_col = f"{rw_mode}_iops"
    bw_col = f"{rw_mode}_bandwidth"
    label_col = f"{rw_mode}_label"

    df[iops_col] = df[iops_col] / 1000
    df[label_col] = df[bw_col].astype(str) + "GB/s," + df[iops_col].astype(str) + "Kiops"

    if metric_mode == "bandwidth":
        df["computed"] = df["rate"] / df["cost"] * 1000 * 131072 / 1024 / 1024 / 1024
        ylabel = "Bandwidth (GB/s)"
        title = f"Real vs Configured {rw_mode.capitalize()} Bandwidth"
        value_col = df[bw_col]
    else:
        df["computed"] = df["rate"] / df["cost"] * 1000
        ylabel = "IOPS"
        title = f"Real vs Configured {rw_mode.capitalize()} IOPS"
        value_col = df[iops_col] * 1000

    fig, ax = plt.subplots(figsize=(12, 6))
    x = df[label_col]
    x_pos = range(len(x))

    ax.bar([p - 0.2 for p in x_pos], df["computed"], width=0.4, label=f"Real {metric_mode.upper()}", align='center')
    ax.bar([p + 0.2 for p in x_pos], value_col, width=0.4, label=f"Configured {metric_mode.upper()}", align='center')

    ax.set_xticks(x_pos)
    ax.set_xticklabels(x, rotation=90, ha='center', fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title} (Latency Goal = 1)")
    ax.legend()
    plt.tight_layout()
    filename = f"{metric_mode}_vs_computed_{rw_mode}.png"
    plt.savefig(os.path.join(output_dir, filename))
    print(f"Saved {metric_mode.upper()} vs computed {rw_mode} bar chart")
    plt.close()

# Example usage:
generate_csv(read_csv_path, "read", "bandwidth")
plot_vs_computed(read_csv_path, "read", "bandwidth")
generate_csv(read_csv_path, "read", "iops")
plot_vs_computed(read_csv_path, "read", "iops")
generate_csv(write_csv_path, "write", "bandwidth")
plot_vs_computed(write_csv_path, "write", "bandwidth")
generate_csv(write_csv_path, "write", "iops")
plot_vs_computed(write_csv_path, "write", "iops")

