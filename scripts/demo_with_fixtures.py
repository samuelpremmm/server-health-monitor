#!/usr/bin/env python3
"""Run the full report pipeline on any OS using the sample /proc files.

Useful for a demo on Windows/macOS. On a real Linux server use
`python3 -m health_monitor` instead.

    python scripts/demo_with_fixtures.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from health_monitor import cpu, disk, memory, report, sysinfo  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")


def main():
    first = cpu.read_cpu_times(os.path.join(FIX, "stat_1"))
    second = cpu.read_cpu_times(os.path.join(FIX, "stat_2"))
    cpu_data = {
        "usage_percent": cpu.calculate_usage(first, second),
        "cores": os.cpu_count() or 1,
        "load_average": cpu.read_load_average(os.path.join(FIX, "loadavg")),
    }
    system = sysinfo.get_system_info(
        os.path.join(FIX, "os-release"), os.path.join(FIX, "uptime")
    )
    disk_path = os.path.abspath(os.sep)  # "/" on Linux, "C:\" on Windows
    rep = report.build_report(
        system=system,
        cpu=cpu_data,
        memory=memory.get_memory_usage(os.path.join(FIX, "meminfo")),
        disks=disk.get_disk_usage([disk_path]),
    )
    log_file = os.path.join(ROOT, "logs", "demo_health_report.log")
    path = report.save_report(rep, log_file)
    print(report.format_report(rep))
    print(f"\nReport saved to {path}")
    return report.SEVERITY[rep["overall_status"]]


if __name__ == "__main__":
    sys.exit(main())
