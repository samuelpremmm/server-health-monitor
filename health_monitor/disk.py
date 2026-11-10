"""Disk utilization for one or more mount points, using shutil.disk_usage."""

import shutil


def get_disk_usage(paths=("/",)):
    """Return total/used/free bytes and usage % for each path."""
    results = []
    for path in paths:
        try:
            usage = shutil.disk_usage(path)
        except (FileNotFoundError, PermissionError, OSError) as exc:
            results.append({"path": path, "error": str(exc)})
            continue
        percent = round(usage.used / usage.total * 100, 1) if usage.total else 0.0
        results.append(
            {
                "path": path,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "usage_percent": percent,
            }
        )
    return results
