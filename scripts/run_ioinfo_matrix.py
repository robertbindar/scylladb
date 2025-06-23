import os
import subprocess
import re
import csv
from itertools import product
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration ranges (logarithmic doubling)
latency_goals = [x for x in [2 ** i for i in range(0, 9)]]  # 1 to 256 us
read_iops_bandwidth_pairs = [(100000 * 2 ** i, f"{2 ** i}G") for i in range(0, 22)]  # (1024,1G), (2048,2G), ...

# Disk mount point
mountpoint = "/var/lib/scylla/robitza"

# Directory for generated files
output_dir = "iotune_configs"
os.makedirs(output_dir, exist_ok=True)

# CSV log file path
csv_path = os.path.join(output_dir, "iotune_results.csv")

# YAML template
yaml_template = """
disks:
  - mountpoint: {mountpoint}
    read_iops: {read_iops}
    read_bandwidth: {read_bw}
    write_iops: 1000
    write_bandwidth: 1000M
"""

# Single YAML path
yaml_path = os.path.join(output_dir, "io-properties.yaml")

def generate_csv():
    with open(csv_path, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["latency_goal", "read_iops", "read_bandwidth", "rate", "cost", "read_req_per_sec"])

        # Execute ioinfo commands directly
        for latency in latency_goals:
            for read_iops, read_bw in read_iops_bandwidth_pairs:
                # Overwrite the same YAML file
                with open(yaml_path, "w") as f:
                    f.write(yaml_template.format(mountpoint=mountpoint, read_iops=read_iops, read_bw=read_bw))

                # Build the command
                cmd = [
                    "sudo", "./build/release/seastar/apps/io_tester/ioinfo",
                    f"--directory={mountpoint}",
                    f"--io-properties-file={yaml_path}",
                    f"--io-latency-goal={latency}"
                ]

                # Run the command and capture output
                try:
                    print(f"Running ioinfo with latency={latency}, read_iops={read_iops}, read_bw={read_bw}...")
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    output = result.stdout

                    # Parse token bucket rate and read cost for 131072
                    rate_match = re.search(r" rate:\s*(\d+)", output)
                    cost_match = re.search(r"131072:\s*\n\s*read:\s*(\d+)", output)

                    if rate_match and cost_match:
                        rate = int(rate_match.group(1))
                        cost = int(cost_match.group(1))
                        if cost == 0:
                            print('Cost was zero, req_per_sec to 0')
                            req_per_sec = 0
                        else:
                            req_per_sec = rate / cost * 1000
                        print(f"Estimated read req/sec for 128k buffer: {req_per_sec:.2f} r/s")
                        writer.writerow([latency, read_iops, read_bw, rate, cost, req_per_sec])
                    else:
                        print("Could not parse rate or cost from output.")

                except subprocess.CalledProcessError as e:
                    print(f"Command failed: {e}")
                    print(f"Standard Error Output:\n{e.stderr}")

    print(f"Completed running ioinfo for all configurations using a single YAML file in '{output_dir}'.")

# Function to plot heatmap from CSV results
def plot_heatmap(csv_path):
    df = pd.read_csv(csv_path)

    # Sort by read_iops before pivoting to ensure y-axis is ordered numerically
    df = df.sort_values(by='read_iops', ascending=False)
    df['read_req_per_sec'] = df['read_req_per_sec'] / 1000

    pivot = df.pivot(index=['read_iops', 'read_bandwidth'], columns='latency_goal', values='read_req_per_sec')

    plt.figure(figsize=(12, 8))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="viridis")
    plt.title("Read Requests/sec Heatmap")
    plt.xlabel("Latency Goal (us)")
    plt.ylabel("Bandwidth,IOPS")
    plt.tight_layout()

    # Save plot as PNG
    heatmap_path = os.path.join(output_dir, "heatmap.png")
    plt.savefig(heatmap_path)
    print(f"Heatmap saved to {heatmap_path}")
    plt.close()

# Run generation and plotting
generate_csv()
plot_heatmap(csv_path)

