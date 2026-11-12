# Server Health Monitor - web dashboard in a container.
#
# Build:  docker build -t health-monitor .
# Run:    docker run -d --name health-monitor -p 5000:5000 \
#           --hostname "$(hostname)" -v /:/host:ro -e DISK_PATHS=/host \
#           --restart unless-stopped health-monitor
#
# /proc/stat, /proc/meminfo and /proc/loadavg inside a container already show the
# host's CPU and memory. The read-only /host mount lets it report the host's disk.

FROM python:3.12-slim

# Don't write .pyc files, and print logs straight away (no buffering)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

# Only the code the app needs (see .dockerignore). No pip install: stdlib only.
COPY health_monitor/ health_monitor/
COPY tests/fixtures/ tests/fixtures/

# Run as a normal user, not root
RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 5000

# Docker marks the container "unhealthy" if /healthz stops answering
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','5000'), timeout=4)" || exit 1

CMD ["python", "-m", "health_monitor.web"]
