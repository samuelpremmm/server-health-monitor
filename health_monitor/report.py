"""Build the health report, evaluate thresholds and save it to a log file."""

import json
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

OK, WARNING, CRITICAL = "OK", "WARNING", "CRITICAL"
SEVERITY = {OK: 0, WARNING: 1, CRITICAL: 2}

DEFAULT_THRESHOLDS = {
    "cpu": {"warning": 75.0, "critical": 90.0},
    "memory": {"warning": 75.0, "critical": 90.0},
    "disk": {"warning": 80.0, "critical": 90.0},
}


def evaluate(value, warning, critical):
    """Return OK / WARNING / CRITICAL for a usage percentage."""
    if value >= critical:
        return CRITICAL
    if value >= warning:
        return WARNING
    return OK


def human_bytes(num):
    """Format bytes as a readable size, e.g. 7.6 GB."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024 or unit == "TB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024
    return f"{num:.1f} TB"


def build_report(system, cpu, memory, disks, thresholds=None, timestamp=None):
    """Combine all checks into one report dict with an overall status."""
    t = thresholds or DEFAULT_THRESHOLDS
    timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cpu_status = evaluate(cpu["usage_percent"], **t["cpu"])
    mem_status = evaluate(memory["usage_percent"], **t["memory"])
    for d in disks:
        d["status"] = (
            CRITICAL if "error" in d else evaluate(d["usage_percent"], **t["disk"])
        )

    statuses = [cpu_status, mem_status] + [d["status"] for d in disks]
    overall = max(statuses, key=lambda s: SEVERITY[s])

    return {
        "timestamp": timestamp,
        "overall_status": overall,
        "system": system,
        "cpu": {**cpu, "status": cpu_status},
        "memory": {**memory, "status": mem_status},
        "disks": disks,
        "thresholds": t,
    }


def format_report(report):
    """Render the report as a readable text block."""
    s, c, m = report["system"], report["cpu"], report["memory"]
    la = c["load_average"]
    line = "=" * 60
    out = [
        line,
        "              LINUX SERVER HEALTH REPORT",
        line,
        f"Generated     : {report['timestamp']}",
        f"Overall status: {report['overall_status']}",
        "",
        "[ SYSTEM INFORMATION ]",
        f"  Hostname     : {s['hostname']}",
        f"  OS           : {s['os']}",
        f"  Kernel       : {s['kernel']}",
        f"  Architecture : {s['architecture']}",
        f"  IP address   : {s['ip_address']}",
        f"  Uptime       : {s['uptime']}",
        f"  Python       : {s['python_version']}",
        "",
        f"[ CPU ]                                   {c['status']}",
        f"  Usage        : {c['usage_percent']:.1f} %",
        f"  Cores        : {c['cores']}",
        f"  Load average : {la['1min']:.2f} (1m)  {la['5min']:.2f} (5m)  "
        f"{la['15min']:.2f} (15m)",
        "",
        f"[ MEMORY ]                                {m['status']}",
        f"  Usage        : {m['usage_percent']:.1f} %",
        f"  Used / Total : {human_bytes(m['used'])} / {human_bytes(m['total'])}",
        f"  Available    : {human_bytes(m['available'])}",
        f"  Swap         : {human_bytes(m['swap_used'])} / "
        f"{human_bytes(m['swap_total'])} ({m['swap_percent']:.1f} %)",
        "",
        "[ DISK ]",
    ]
    for d in report["disks"]:
        if "error" in d:
            out.append(f"  {d['path']:<12} : ERROR - {d['error']}    {d['status']}")
            continue
        out.append(
            f"  {d['path']:<12} : {d['usage_percent']:.1f} %  "
            f"({human_bytes(d['used'])} used of {human_bytes(d['total'])}, "
            f"{human_bytes(d['free'])} free)    {d['status']}"
        )

    warnings = _collect_alerts(report)
    out += ["", "[ ALERTS ]"]
    out += [f"  - {w}" for w in warnings] if warnings else ["  None - all checks passed."]
    out.append(line)
    return "\n".join(out)


def _collect_alerts(report):
    alerts = []
    t = report["thresholds"]
    if report["cpu"]["status"] != OK:
        alerts.append(
            f"CPU usage {report['cpu']['usage_percent']:.1f}% is {report['cpu']['status']}"
            f" (warning {t['cpu']['warning']}%, critical {t['cpu']['critical']}%)"
        )
    if report["memory"]["status"] != OK:
        alerts.append(
            f"Memory usage {report['memory']['usage_percent']:.1f}% is "
            f"{report['memory']['status']} (warning {t['memory']['warning']}%, "
            f"critical {t['memory']['critical']}%)"
        )
    for d in report["disks"]:
        if "error" in d:
            alerts.append(f"Disk {d['path']} could not be read: {d['error']}")
        elif d["status"] != OK:
            alerts.append(
                f"Disk {d['path']} usage {d['usage_percent']:.1f}% is {d['status']}"
                f" (warning {t['disk']['warning']}%, critical {t['disk']['critical']}%)"
            )
    return alerts


def get_logger(log_file, max_bytes=1_000_000, backups=5):
    """Logger that appends to log_file and rotates it at max_bytes."""
    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
    logger = logging.getLogger(f"health_monitor:{os.path.abspath(log_file)}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    return logger


def save_report(report, log_file, as_json=False):
    """Append the report to log_file (text block or one JSON line)."""
    logger = get_logger(log_file)
    text = json.dumps(report) if as_json else format_report(report) + "\n"
    logger.info(text)
    for h in logger.handlers:
        h.flush()
    return os.path.abspath(log_file)
