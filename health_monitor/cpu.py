"""CPU utilization.

CPU usage is calculated from two samples of /proc/stat taken `interval` seconds
apart. The first line of /proc/stat looks like:

    cpu  user nice system idle iowait irq softirq steal guest guest_nice

Usage % = (1 - idle_delta / total_delta) * 100, where "idle" includes iowait.
"""

import os
import time

PROC_STAT = "/proc/stat"
PROC_LOADAVG = "/proc/loadavg"


def read_cpu_times(path=PROC_STAT):
    """Return (idle, total) jiffies from the aggregate 'cpu' line of /proc/stat."""
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("cpu "):
                values = [int(v) for v in line.split()[1:]]
                break
        else:
            raise ValueError(f"No aggregate 'cpu' line found in {path}")

    # guest and guest_nice are already counted inside user/nice, so ignore them.
    values = values[:8]
    idle = values[3] + (values[4] if len(values) > 4 else 0)  # idle + iowait
    total = sum(values)
    return idle, total


def calculate_usage(first, second):
    """Calculate CPU usage % between two (idle, total) samples."""
    idle_delta = second[0] - first[0]
    total_delta = second[1] - first[1]
    if total_delta <= 0:
        return 0.0
    return round((1 - idle_delta / total_delta) * 100, 1)


def read_load_average(path=PROC_LOADAVG):
    """Return the 1, 5 and 15 minute load averages."""
    with open(path, encoding="utf-8") as f:
        one, five, fifteen = (float(v) for v in f.read().split()[:3])
    return {"1min": one, "5min": five, "15min": fifteen}


def get_cpu_usage(interval=1.0, stat_path=PROC_STAT, loadavg_path=PROC_LOADAVG):
    """Return CPU usage %, core count and load averages."""
    first = read_cpu_times(stat_path)
    time.sleep(interval)
    second = read_cpu_times(stat_path)
    return {
        "usage_percent": calculate_usage(first, second),
        "cores": os.cpu_count() or 1,
        "load_average": read_load_average(loadavg_path),
    }
