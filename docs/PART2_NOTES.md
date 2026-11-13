# Part 2 Notes: Dashboard + systemd + Docker

## What we built
Turned the health monitor into a **web dashboard** that runs **24/7** on AWS EC2 inside a **Docker container**.

- **Dashboard** = a web page showing CPU, memory, disk and system info (port 5000)
- **systemd** = Linux service manager; keeps an app running and starts it at boot
- **Docker** = packs the app into a container so it runs the same on any server
- **Image** = the recipe (built once). **Container** = the running app made from it

## Commands

| Command | Meaning |
|---|---|
| `git pull` | Get the latest code from GitHub |
| `python3 -m health_monitor.web` | Start the dashboard (Ctrl+C to stop) |
| `sudo systemctl enable --now health-dashboard` | Run it as a service: start now + at boot |
| `systemctl status health-dashboard` | Check the service is running |
| `sudo systemctl disable --now health-dashboard` | Stop the service (to free port 5000 for Docker) |
| `sudo apt install -y docker.io docker-buildx` | Install Docker |
| `docker build -t health-monitor .` | Build an image from the Dockerfile |
| `docker run -d --name health-monitor -p 5000:5000 ...` | Start a container |
| `docker ps` | List running containers (`healthy` = working) |
| `docker rm -f health-monitor` | Delete the container (to run it again) |

**docker run options:** `-d` background · `--name` give a name · `-p 5000:5000` open port · `-v /:/host:ro` read the server disk (read-only) · `--restart unless-stopped` auto restart

## Errors and fixes

**1. permission denied (docker.sock)**
- Why: my user was not in the `docker` group (`groups` did not show `docker`)
- Fix:
  - `sudo usermod -aG docker ubuntu` → add my user to the docker group
  - `newgrp docker` → apply it now without logging out

**2. Conflict: container name already in use**
- Why: I ran `docker run` twice; the first container was already running
- Fix: nothing to fix. To recreate: `docker rm -f health-monitor`, then `docker run` again

**3. DEPRECATED: legacy builder**
- Why: BuildKit was not installed (only a warning)
- Fix: `sudo apt install -y docker-buildx`

## Interview line
"I built a web dashboard for my monitoring tool, ran it with systemd, then containerized it with Docker on AWS EC2 with a health check and auto-restart. I fixed a Docker permission error by adding my user to the docker group."

## Tomorrow
1. Start EC2 instance → copy new public IP → check my IP in the security group
2. Open `http://<new-ip>:5000` (Docker container starts by itself)
3. Write the Part 2 LinkedIn post
4. Start Part 3: CI/CD (auto deploy to EC2 on git push)
