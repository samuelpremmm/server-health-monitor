"""Command-line entry point.

    python3 -m health_monitor                    # one report, printed and logged
    python3 -m health_monitor --disk / --disk /home
    python3 -m health_monitor --watch 60         # repeat every 60 seconds
    python3 -m health_monitor --json             # JSON output

Exit code: 0 = OK, 1 = WARNING, 2 = CRITICAL (handy for cron and alerting).
"""

import argparse
import json
import sys
import time

from . import __version__
from .cpu import get_cpu_usage
from .disk import get_disk_usage
from .memory import get_memory_usage
from .report import DEFAULT_THRESHOLDS, SEVERITY, build_report, format_report, save_report
from .sysinfo import get_system_info


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="health_monitor",
        description="Check Linux server CPU, memory and disk health and log a report.",
    )
    p.add_argument("--disk", action="append", metavar="PATH",
                   help="mount point to check (repeatable, default: /)")
    p.add_argument("--log-file", default="logs/health_report.log",
                   help="where to append reports (default: logs/health_report.log)")
    p.add_argument("--interval", type=float, default=1.0,
                   help="seconds between CPU samples (default: 1)")
    p.add_argument("--watch", type=float, metavar="SECONDS",
                   help="keep running, one report every SECONDS")
    p.add_argument("--json", action="store_true", help="print and log JSON instead of text")
    p.add_argument("--quiet", action="store_true", help="only write the log file")
    p.add_argument("--cpu-warn", type=float, default=DEFAULT_THRESHOLDS["cpu"]["warning"])
    p.add_argument("--cpu-crit", type=float, default=DEFAULT_THRESHOLDS["cpu"]["critical"])
    p.add_argument("--mem-warn", type=float, default=DEFAULT_THRESHOLDS["memory"]["warning"])
    p.add_argument("--mem-crit", type=float, default=DEFAULT_THRESHOLDS["memory"]["critical"])
    p.add_argument("--disk-warn", type=float, default=DEFAULT_THRESHOLDS["disk"]["warning"])
    p.add_argument("--disk-crit", type=float, default=DEFAULT_THRESHOLDS["disk"]["critical"])
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p.parse_args(argv)


def run_once(args):
    thresholds = {
        "cpu": {"warning": args.cpu_warn, "critical": args.cpu_crit},
        "memory": {"warning": args.mem_warn, "critical": args.mem_crit},
        "disk": {"warning": args.disk_warn, "critical": args.disk_crit},
    }
    report = build_report(
        system=get_system_info(),
        cpu=get_cpu_usage(interval=args.interval),
        memory=get_memory_usage(),
        disks=get_disk_usage(args.disk or ["/"]),
        thresholds=thresholds,
    )
    path = save_report(report, args.log_file, as_json=args.json)
    if not args.quiet:
        print(json.dumps(report, indent=2) if args.json else format_report(report))
        print(f"\nReport saved to {path}")
    return SEVERITY[report["overall_status"]]


def main(argv=None):
    args = parse_args(argv)
    if not sys.platform.startswith("linux"):
        print("This tool reads /proc and must run on Linux.", file=sys.stderr)
        return 3
    try:
        if args.watch:
            while True:
                run_once(args)
                time.sleep(args.watch)
        return run_once(args)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
