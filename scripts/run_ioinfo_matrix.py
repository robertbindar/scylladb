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
read_iops_values = [100000 * 2 ** i for i in range(0, 6)]
read_bandwidth_values = [2 ** i for i in range(0, 6)]
write_iops_values = read_iops_values
write_bandwidth_values = read_bandwidth_values

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

def parse_output(output, latency, iops, bw, mode):
    if output is None:
        return None

    if mode == "read":
        rate_match = re.search(r" rate:\s*(\d+)", output)
        cost_match = re.search(r"131072:\s*\n\s*read:\s*(\d+)", output)
    else:
        rate_match = re.search(r" rate:\s*(\d+)", output)
        cost_match = re.search(r"131072:\s*\n\s*read:\s*(\d+)\n\s*write:\s*(\d+)", output)

    if rate_match and cost_match:
        rate = int(rate_match.group(1))
        if mode == "read":
            cost = int(cost_match.group(1))
        else:
            cost = int(cost_match.group(2))

        req_per_sec = 0 if cost == 0 else rate / cost * 1000
        return [latency, iops, bw, rate, cost, req_per_sec]
    else:
        print("Could not parse rate or cost from output.")
        return None

def generate_read_csv():
    with open(read_csv_path, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["latency_goal", "read_iops", "read_bandwidth", "rate", "cost", "read_req_per_sec"])

        for latency in latency_goals:
            for read_iops, read_bw in product(read_iops_values, read_bandwidth_values):
                output = run_ioinfo(read_iops, read_bw, 1000, 1, latency, "read")
                row = parse_output(output, latency, read_iops, read_bw, "read")
                if row:
                    writer.writerow(row)

def generate_write_csv():
    with open(write_csv_path, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["latency_goal", "write_iops", "write_bandwidth", "rate", "cost", "write_req_per_sec"])

        for latency in latency_goals:
            for write_iops, write_bw in product(write_iops_values, write_bandwidth_values):
                output = run_ioinfo(100000, 1, write_iops, write_bw, latency, "write")
                row = parse_output(output, latency, write_iops, write_bw, "write")
                if row:
                    writer.writerow(row)

def plot_bandwidth_vs_computed(csv_path, mode):
    df = pd.read_csv(csv_path)
    df["computed"] = df["rate"] / df["cost"] * 1000 * 131072 / 1024 / 1024 / 1024
    iops_col = f"{mode}_iops"
    bw_col = f"{mode}_bandwidth"
    df[iops_col] = df[iops_col] / 1000
    df["label"] = df[bw_col].astype(str) + "GB/s," + df[iops_col].astype(str) + "Kiops"

    fig, ax = plt.subplots(figsize=(12, 6))
    x = df["label"]
    x_pos = range(len(x))

    ax.bar([p - 0.2 for p in x_pos], df["computed"], width=0.4, label="Real bandwidth", align='center')
    ax.bar([p + 0.2 for p in x_pos], df[bw_col], width=0.4, label="Configured bandwidth", align='center')

    ax.set_xticks(x_pos)
    ax.set_xticklabels(x, rotation=90, ha='center', fontsize=8)
    ax.set_ylabel("Bandwidth (GB/s)")
    ax.set_title(f"Real vs Configured {mode.capitalize()} Bandwidth (Latency Goal = 1)")
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"bandwidth_vs_computed_{mode}.png"))
    print(f"Saved bandwidth vs computed {mode} bar chart")
    plt.close()

# Uncomment to generate data
generate_read_csv()
generate_write_csv()

# Uncomment to plot
plot_bandwidth_vs_computed(read_csv_path, "read")
plot_bandwidth_vs_computed(write_csv_path, "write")

