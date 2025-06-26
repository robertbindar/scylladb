import os
import subprocess
import csv

# Configuration
reqsizes = ["128kB", "1MB"]  # 128KB and 1MB as strings
parallelisms = [1, 2, 4, 8, 16, 32, 64]

mountpoint = "/var/lib/scylla/robitza"
yaml_path = "io_tester_conf.yaml"
csv_path = "io_tester_output.csv"

# Template for YAML
yaml_template = """- name: big_reads
  shards: all
  type: seqread
  data_size: 10GB
  shard_info:
    parallelism: {parallelism}
    reqsize: {reqsize}
"""

# Write CSV header
with open(csv_path, mode="w", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["reqsize", "parallelism", "output"])

    # Loop through all combinations
    for reqsize in reqsizes:
        for parallelism in parallelisms:
            # Write YAML config
            with open(yaml_path, "w") as f:
                f.write(yaml_template.format(
                    reqsize=reqsize,
                    parallelism=parallelism
                ))

            # Run the command
            cmd = [
                "sudo", "./build/release/seastar/apps/io_tester/io_tester",
                f"--storage={mountpoint}",
                f"--conf={yaml_path}",
                "--duration=60",
                "--smp=1"
            ]

            try:
                print(f"Running for reqsize={reqsize}, parallelism={parallelism}...")
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                print(result)
                output = result.stdout.strip()
            except subprocess.CalledProcessError as e:
                output = f"ERROR: {e.stderr.strip()}"

            # Write to CSV
            writer.writerow([reqsize, parallelism, output])
            print(f"Logged result for reqsize={reqsize}, parallelism={parallelism}")

