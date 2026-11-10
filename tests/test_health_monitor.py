"""Unit tests. Run with:  python3 -m unittest discover -s tests -v

The tests use saved copies of /proc files in tests/fixtures, so the parsing
logic can be checked on any machine.
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from health_monitor import cpu, disk, memory, report, sysinfo

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def fx(name):
    return os.path.join(FIX, name)


class TestCPU(unittest.TestCase):
    def test_read_cpu_times(self):
        idle, total = cpu.read_cpu_times(fx("stat_1"))
        self.assertEqual(idle, 8500)   # idle 8000 + iowait 500
        self.assertEqual(total, 10000)

    def test_calculate_usage(self):
        first = cpu.read_cpu_times(fx("stat_1"))
        second = cpu.read_cpu_times(fx("stat_2"))
        # total delta 1000, idle delta 600 -> 40% busy
        self.assertEqual(cpu.calculate_usage(first, second), 40.0)

    def test_calculate_usage_no_change(self):
        self.assertEqual(cpu.calculate_usage((10, 100), (10, 100)), 0.0)

    def test_load_average(self):
        la = cpu.read_load_average(fx("loadavg"))
        self.assertEqual(la, {"1min": 0.52, "5min": 0.38, "15min": 0.30})

    def test_get_cpu_usage(self):
        samples = iter([(8500, 10000), (9100, 11000)])
        with mock.patch.object(cpu, "read_cpu_times", side_effect=lambda p: next(samples)), \
             mock.patch.object(cpu.time, "sleep"):
            result = cpu.get_cpu_usage(interval=0, loadavg_path=fx("loadavg"))
        self.assertEqual(result["usage_percent"], 40.0)
        self.assertGreaterEqual(result["cores"], 1)


class TestMemory(unittest.TestCase):
    def test_memory_usage(self):
        m = memory.get_memory_usage(fx("meminfo"))
        self.assertEqual(m["total"], 8000000 * 1024)
        self.assertEqual(m["available"], 2000000 * 1024)
        self.assertEqual(m["used"], 6000000 * 1024)
        self.assertEqual(m["usage_percent"], 75.0)
        self.assertEqual(m["swap_percent"], 25.0)

    def test_fallback_without_memavailable(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
            f.write("MemTotal: 1000 kB\nMemFree: 200 kB\nBuffers: 100 kB\nCached: 200 kB\n")
        try:
            m = memory.get_memory_usage(f.name)
            self.assertEqual(m["usage_percent"], 50.0)
            self.assertEqual(m["swap_percent"], 0.0)
        finally:
            os.remove(f.name)


class TestDisk(unittest.TestCase):
    def test_disk_usage(self):
        fake = mock.Mock(total=100, used=85, free=15)
        with mock.patch.object(disk.shutil, "disk_usage", return_value=fake):
            d = disk.get_disk_usage(["/"])[0]
        self.assertEqual(d["usage_percent"], 85.0)
        self.assertEqual(d["free"], 15)

    def test_missing_path(self):
        d = disk.get_disk_usage(["/definitely/not/a/real/path"])[0]
        self.assertIn("error", d)


class TestSysInfo(unittest.TestCase):
    def test_os_name(self):
        self.assertEqual(sysinfo.read_os_name(fx("os-release")), "Ubuntu 24.04 LTS")

    def test_uptime(self):
        seconds = sysinfo.read_uptime_seconds(fx("uptime"))
        self.assertEqual(sysinfo.format_uptime(seconds), "3 days, 4 hours, 0 minutes")

    def test_format_uptime_unknown(self):
        self.assertEqual(sysinfo.format_uptime(None), "unknown")

    def test_get_system_info_keys(self):
        info = sysinfo.get_system_info(fx("os-release"), fx("uptime"))
        for key in ("hostname", "os", "kernel", "architecture", "ip_address", "uptime"):
            self.assertIn(key, info)


def sample_report(cpu_pct=40.0, mem_pct=75.0, disk_pct=50.0):
    return report.build_report(
        system={"hostname": "web-01", "os": "Ubuntu 24.04 LTS", "kernel": "6.8.0",
                "architecture": "x86_64", "ip_address": "10.0.0.5",
                "uptime": "3 days", "python_version": "3.12.3"},
        cpu={"usage_percent": cpu_pct, "cores": 2,
             "load_average": {"1min": 0.5, "5min": 0.4, "15min": 0.3}},
        memory={"total": 8 * 1024**3, "used": 6 * 1024**3, "available": 2 * 1024**3,
                "usage_percent": mem_pct, "swap_total": 0, "swap_used": 0,
                "swap_percent": 0.0},
        disks=[{"path": "/", "total": 100 * 1024**3, "used": 50 * 1024**3,
                "free": 50 * 1024**3, "usage_percent": disk_pct}],
        timestamp="2026-11-10 10:00:00",
    )


class TestReport(unittest.TestCase):
    def test_evaluate(self):
        self.assertEqual(report.evaluate(50, 75, 90), report.OK)
        self.assertEqual(report.evaluate(75, 75, 90), report.WARNING)
        self.assertEqual(report.evaluate(95, 75, 90), report.CRITICAL)

    def test_overall_status_is_worst(self):
        self.assertEqual(sample_report()["overall_status"], report.WARNING)  # memory 75%
        self.assertEqual(sample_report(mem_pct=10)["overall_status"], report.OK)
        self.assertEqual(sample_report(disk_pct=95)["overall_status"], report.CRITICAL)

    def test_human_bytes(self):
        self.assertEqual(report.human_bytes(512), "512 B")
        self.assertEqual(report.human_bytes(1536), "1.5 KB")
        self.assertEqual(report.human_bytes(8 * 1024**3), "8.0 GB")

    def test_format_report(self):
        text = report.format_report(sample_report())
        self.assertIn("LINUX SERVER HEALTH REPORT", text)
        self.assertIn("web-01", text)
        self.assertIn("Memory usage 75.0% is WARNING", text)

    def test_save_report_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "logs", "health.log")
            report.save_report(sample_report(), log)
            report.save_report(sample_report(), log)
            with open(log, encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(content.count("LINUX SERVER HEALTH REPORT"), 2)
            for h in report.get_logger(log).handlers:
                h.close()

    def test_save_report_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = os.path.join(tmp, "health.jsonl")
            report.save_report(sample_report(), log, as_json=True)
            with open(log, encoding="utf-8") as f:
                data = json.loads(f.readline())
            self.assertEqual(data["system"]["hostname"], "web-01")
            for h in report.get_logger(log).handlers:
                h.close()


if __name__ == "__main__":
    unittest.main()
