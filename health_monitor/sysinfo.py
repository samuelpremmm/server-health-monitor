"""System information: hostname, OS, kernel, architecture, uptime, IP, Python."""

import platform
import socket

PROC_UPTIME = "/proc/uptime"
OS_RELEASE = "/etc/os-release"


def read_os_name(path=OS_RELEASE):
    """Return PRETTY_NAME from /etc/os-release, e.g. 'Ubuntu 24.04 LTS'."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return f"{platform.system()} {platform.release()}"


def read_uptime_seconds(path=PROC_UPTIME):
    """Return system uptime in seconds, or None if unavailable."""
    try:
        with open(path, encoding="utf-8") as f:
            return float(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def format_uptime(seconds):
    """Turn seconds into '3 days, 4 hours, 5 minutes'."""
    if seconds is None:
        return "unknown"
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return ", ".join(parts)


def get_ip_address():
    """Return the primary IPv4 address (no packets are actually sent)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def get_system_info(os_release_path=OS_RELEASE, uptime_path=PROC_UPTIME):
    """Collect basic system information."""
    uptime = read_uptime_seconds(uptime_path)
    return {
        "hostname": socket.gethostname(),
        "os": read_os_name(os_release_path),
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "ip_address": get_ip_address(),
        "uptime_seconds": uptime,
        "uptime": format_uptime(uptime),
        "python_version": platform.python_version(),
    }
