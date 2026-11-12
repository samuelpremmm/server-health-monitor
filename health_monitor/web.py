"""Web dashboard for the health monitor (standard library only, no Flask).

    python3 -m health_monitor.web                 # http://<server>:5000
    python3 -m health_monitor.web --port 8080
    python3 -m health_monitor.web --demo          # sample data, works on Windows/macOS

Routes:
    /             dashboard page (refreshes itself every few seconds)
    /api/health   the full report as JSON
    /healthz      tiny "is the app alive?" check for Docker / load balancers
"""

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__, cpu, disk, memory, report, sysinfo

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "tests", "fixtures")


def live_report(interval=0.5, disks=("/",)):
    """Collect real metrics from /proc (Linux only)."""
    return report.build_report(
        system=sysinfo.get_system_info(),
        cpu=cpu.get_cpu_usage(interval=interval),
        memory=memory.get_memory_usage(),
        disks=disk.get_disk_usage(list(disks)),
    )


def demo_report():
    """Build a report from the sample /proc files in tests/fixtures (any OS)."""
    fx = lambda name: os.path.join(FIXTURES, name)  # noqa: E731
    first = cpu.read_cpu_times(fx("stat_1"))
    second = cpu.read_cpu_times(fx("stat_2"))
    return report.build_report(
        system=sysinfo.get_system_info(fx("os-release"), fx("uptime")),
        cpu={
            "usage_percent": cpu.calculate_usage(first, second),
            "cores": os.cpu_count() or 1,
            "load_average": cpu.read_load_average(fx("loadavg")),
        },
        memory=memory.get_memory_usage(fx("meminfo")),
        disks=disk.get_disk_usage([os.path.abspath(os.sep)]),
    )


class CachedCollector:
    """Run the collector at most once every `ttl` seconds, however many people refresh."""

    def __init__(self, collect, ttl=2.0):
        self._collect = collect
        self._ttl = ttl
        self._lock = threading.Lock()
        self._value = None
        self._at = 0.0

    def __call__(self):
        with self._lock:
            if self._value is None or time.monotonic() - self._at >= self._ttl:
                rep = self._collect()
                rep["alerts"] = report._collect_alerts(rep)
                self._value, self._at = rep, time.monotonic()
            return self._value


def make_handler(collector):
    class Handler(BaseHTTPRequestHandler):
        server_version = f"health-monitor/{__version__}"

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/":
                self._send(200, "text/html; charset=utf-8", DASHBOARD_HTML.encode())
            elif path == "/api/health":
                try:
                    body = json.dumps(collector()).encode()
                except Exception as exc:  # report the error instead of crashing the server
                    self._send(500, "application/json",
                               json.dumps({"error": str(exc)}).encode())
                    return
                self._send(200, "application/json", body)
            elif path == "/healthz":
                self._send(200, "application/json", b'{"status": "ok"}')
            else:
                self._send(404, "application/json", b'{"error": "not found"}')

        def _send(self, code, content_type, body):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):  # one short line per request
            sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    return Handler


def make_server(host="0.0.0.0", port=5000, collector=None):
    collector = collector or CachedCollector(live_report)
    return ThreadingHTTPServer((host, port), make_handler(collector))


def main(argv=None):
    p = argparse.ArgumentParser(prog="health_monitor.web",
                                description="Serve the health dashboard over HTTP.")
    p.add_argument("--host", default="0.0.0.0",
                   help="address to listen on (default: 0.0.0.0 = all interfaces)")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)),
                   help="port to listen on (default: 5000 or $PORT)")
    p.add_argument("--disk", action="append", metavar="PATH",
                   help="mount point to check (repeatable, default: / or $DISK_PATHS)")
    p.add_argument("--demo", action="store_true",
                   help="use sample data from tests/fixtures (works on any OS)")
    args = p.parse_args(argv)

    if not args.demo and not sys.platform.startswith("linux"):
        print("Live mode reads /proc and must run on Linux. Use --demo here.", file=sys.stderr)
        return 3

    disks = args.disk or os.environ.get("DISK_PATHS", "/").split(",")
    collector = CachedCollector(demo_report if args.demo else lambda: live_report(disks=disks))
    server = make_server(args.host, args.port, collector)
    mode = "demo data" if args.demo else "live data"
    print(f"Health dashboard ({mode}) on http://{args.host}:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Server Health</title>
<style>
  :root { --bg:#0f1419; --card:#1a2129; --line:#2a333d; --text:#e6e9ec; --muted:#8b96a3;
          --ok:#2ea043; --warn:#d29922; --crit:#f85149; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text);
         font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 1000px; margin: 0 auto; padding: 24px 16px 48px; }
  header { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:12px;
           margin-bottom: 20px; }
  h1 { font-size: 22px; margin: 0; }
  .sub { color: var(--muted); font-size: 13px; }
  .badge { padding: 6px 14px; border-radius: 999px; font-weight: 700; font-size: 14px;
           letter-spacing: .04em; background: var(--line); }
  .OK { --c: var(--ok); } .WARNING { --c: var(--warn); } .CRITICAL { --c: var(--crit); }
  .badge.OK, .badge.WARNING, .badge.CRITICAL { background: var(--c); color: #fff; }
  .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 18px; }
  .card h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted);
             margin: 0 0 10px; display:flex; justify-content:space-between; }
  .card h2 span { color: var(--c, var(--muted)); }
  .big { font-size: 34px; font-weight: 700; font-variant-numeric: tabular-nums; }
  .bar { height: 8px; background: var(--line); border-radius: 4px; overflow: hidden; margin: 10px 0; }
  .bar div { height: 100%; width: 0; background: var(--c, var(--ok)); transition: width .4s; }
  .detail { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  td { padding: 6px 0; border-bottom: 1px solid var(--line); vertical-align: top; }
  td:first-child { color: var(--muted); width: 40%; }
  tr:last-child td { border-bottom: 0; }
  .wide { grid-column: 1 / -1; }
  ul { margin: 0; padding-left: 18px; }
  .err { color: var(--crit); }
</style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>Server Health Monitor</h1>
      <div class="sub" id="updated">Loading…</div>
    </div>
    <div class="badge" id="overall">…</div>
  </header>
  <div class="grid">
    <section class="card" id="cpu-card">
      <h2>CPU <span id="cpu-status"></span></h2>
      <div class="big" id="cpu-pct">–</div>
      <div class="bar"><div id="cpu-bar"></div></div>
      <div class="detail" id="cpu-detail"></div>
    </section>
    <section class="card" id="mem-card">
      <h2>Memory <span id="mem-status"></span></h2>
      <div class="big" id="mem-pct">–</div>
      <div class="bar"><div id="mem-bar"></div></div>
      <div class="detail" id="mem-detail"></div>
    </section>
    <div id="disks" style="display:contents"></div>
    <section class="card">
      <h2>System</h2>
      <table><tbody id="sys"></tbody></table>
    </section>
    <section class="card">
      <h2>Alerts</h2>
      <div id="alerts" class="detail"></div>
    </section>
  </div>
</main>
<script>
const REFRESH_MS = 5000;
const $ = (id) => document.getElementById(id);

function size(n) {
  const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0;
  while (Math.abs(n) >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return i ? n.toFixed(1) + " " + u[i] : n + " B";
}
function setStatus(card, statusEl, status) {
  card.classList.remove("OK", "WARNING", "CRITICAL"); card.classList.add(status);
  statusEl.textContent = status;
}
function gauge(prefix, pct, status, detail) {
  setStatus($(prefix + "-card"), $(prefix + "-status"), status);
  $(prefix + "-pct").textContent = pct.toFixed(1) + " %";
  $(prefix + "-bar").style.width = Math.min(pct, 100) + "%";
  $(prefix + "-detail").textContent = detail;
}
function diskCard(d) {
  const s = document.createElement("section"); s.className = "card " + d.status;
  const h = document.createElement("h2"); h.textContent = "Disk " + d.path + " ";
  const st = document.createElement("span"); st.textContent = d.status; h.appendChild(st);
  s.appendChild(h);
  if (d.error) {
    const e = document.createElement("div"); e.className = "err"; e.textContent = d.error;
    s.appendChild(e); return s;
  }
  const big = document.createElement("div"); big.className = "big";
  big.textContent = d.usage_percent.toFixed(1) + " %"; s.appendChild(big);
  const bar = document.createElement("div"); bar.className = "bar";
  const fill = document.createElement("div"); fill.style.width = Math.min(d.usage_percent, 100) + "%";
  bar.appendChild(fill); s.appendChild(bar);
  const det = document.createElement("div"); det.className = "detail";
  det.textContent = size(d.used) + " used of " + size(d.total) + " · " + size(d.free) + " free";
  s.appendChild(det);
  return s;
}

async function refresh() {
  try {
    const r = await fetch("/api/health", { cache: "no-store" });
    const rep = await r.json();
    if (!r.ok) throw new Error(rep.error || r.status);

    $("overall").textContent = rep.overall_status;
    $("overall").className = "badge " + rep.overall_status;
    $("updated").textContent = "Report " + rep.timestamp + " · refreshes every " + REFRESH_MS / 1000 + "s";

    const c = rep.cpu, la = c.load_average;
    gauge("cpu", c.usage_percent, c.status,
      c.cores + " cores · load " + la["1min"].toFixed(2) + " / " + la["5min"].toFixed(2) + " / " + la["15min"].toFixed(2));
    const m = rep.memory;
    gauge("mem", m.usage_percent, m.status,
      size(m.used) + " / " + size(m.total) + " · swap " + m.swap_percent.toFixed(1) + " %");

    $("disks").replaceChildren(...rep.disks.map(diskCard));

    const s = rep.system;
    const rows = [["Hostname", s.hostname], ["OS", s.os], ["Kernel", s.kernel],
                  ["Architecture", s.architecture], ["IP address", s.ip_address],
                  ["Uptime", s.uptime], ["Python", s.python_version]];
    $("sys").replaceChildren(...rows.map(([k, v]) => {
      const tr = document.createElement("tr");
      for (const t of [k, v]) { const td = document.createElement("td"); td.textContent = t; tr.appendChild(td); }
      return tr;
    }));

    if (rep.alerts.length) {
      const ul = document.createElement("ul");
      for (const a of rep.alerts) { const li = document.createElement("li"); li.textContent = a; ul.appendChild(li); }
      $("alerts").replaceChildren(ul);
    } else {
      $("alerts").textContent = "None. All checks passed.";
    }
  } catch (e) {
    $("updated").textContent = "Could not load data: " + e.message;
    $("overall").textContent = "OFFLINE"; $("overall").className = "badge CRITICAL";
  }
}
refresh();
setInterval(refresh, REFRESH_MS);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
