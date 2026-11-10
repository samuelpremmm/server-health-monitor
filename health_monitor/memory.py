"""RAM and swap usage, read from /proc/meminfo.

"Used" memory follows the same rule as the `free` command:
    used = MemTotal - MemAvailable
MemAvailable already accounts for reclaimable cache and buffers.
"""

PROC_MEMINFO = "/proc/meminfo"


def read_meminfo(path=PROC_MEMINFO):
    """Parse /proc/meminfo into a dict of values in bytes."""
    info = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            key, _, rest = line.partition(":")
            parts = rest.split()
            if not parts:
                continue
            value = int(parts[0])
            if len(parts) > 1 and parts[1].lower() == "kb":
                value *= 1024
            info[key.strip()] = value
    return info


def _percent(part, whole):
    return round(part / whole * 100, 1) if whole else 0.0


def get_memory_usage(path=PROC_MEMINFO):
    """Return RAM and swap usage in bytes and percent."""
    info = read_meminfo(path)
    total = info["MemTotal"]
    # MemAvailable exists on kernels 3.14+; fall back to free + buffers + cached.
    available = info.get(
        "MemAvailable",
        info.get("MemFree", 0) + info.get("Buffers", 0) + info.get("Cached", 0),
    )
    used = total - available

    swap_total = info.get("SwapTotal", 0)
    swap_used = swap_total - info.get("SwapFree", 0)

    return {
        "total": total,
        "used": used,
        "available": available,
        "usage_percent": _percent(used, total),
        "swap_total": swap_total,
        "swap_used": swap_used,
        "swap_percent": _percent(swap_used, swap_total),
    }
