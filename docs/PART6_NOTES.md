# Part 6 Notes: Monitoring (Prometheus + Grafana + CloudWatch)

## What we built
Before, I could only see my server's health by opening the dashboard.
Now the server is **watched all the time**: live graphs, alert rules, and an **email when something goes wrong**.

```
App /metrics ───┐
node_exporter ──┼──▶ Prometheus (collects every 15s, alert rules) ──▶ Grafana (live graphs)
                │
AWS CloudWatch ─┴──▶ alarm: CPU > 80% ──▶ SNS ──▶ 📧 email to me
```

**Result (CPU stress test):**
| Time | What happened |
|---|---|
| 00:40:00 | Stress test starts: CPU 100% |
| 00:40 | Grafana: CPU tile red, overall status **CRITICAL** |
| 00:42 | Prometheus alert **HighCPU → FIRING** |
| 00:44 | CloudWatch alarm **OK → ALARM** (80.9% > 80%) → 📧 **ALARM email** |
| 00:45 | Stress test stops by itself |
| 00:46 | CloudWatch alarm **ALARM → OK** → 📧 **OK email** |

## Simple meanings
- **Monitoring** = collecting numbers (metrics) about a server all the time, so problems are seen early
- **Metric** = one number over time, like CPU % every 15 seconds
- **/metrics** = a web page where an app lists its metrics in Prometheus text format
- **Prometheus** = collects (**scrapes**) metrics from targets and stores them; can also run **alert rules**
- **Target** = something Prometheus collects from (my app, node_exporter, Prometheus itself)
- **node_exporter** = a small official program that exposes Linux server metrics (network, disk I/O, load)
- **Grafana** = draws graphs and dashboards from Prometheus data
- **Provisioning** = Grafana's data source and dashboard are loaded from files, no clicking
- **CloudWatch** = AWS's own monitoring. EC2 sends CPU, network and status checks every 5 minutes (free)
- **CloudWatch alarm** = watches one metric and changes state: **OK / ALARM / INSUFFICIENT_DATA**
- **SNS (Simple Notification Service)** = sends messages (here: email) when an alarm changes state
- **Subscription confirmation** = AWS emails me first; alerts only arrive after I click **Confirm subscription**

## What I changed
| Where | Change |
|---|---|
| `health_monitor/web.py` | new **`/metrics`** endpoint: CPU, memory, swap, disk, load, status (0/1/2), uptime, version (+ test) |
| `ansible/roles/monitoring` | runs **node_exporter**, **Prometheus** (7-day / 1 GB storage limit, alert rules) and **Grafana** (data source + dashboard from files) as Docker containers |
| `ansible/roles/common` | **1 GB swap file**, a safety net because the server has only 1 GB of RAM |
| `terraform/alerts.tf` | SNS topic + email subscription, alarm **CPU > 80%**, alarm **status check failed** |
| `terraform/security.tf` | ports **3000** (Grafana) and **9090** (Prometheus) open to **my IP only** |
| `terraform/main.tf` | `cpu_credits = "standard"`: the stress test can **never** cost extra money |
| `terraform.tfvars` | my email for alerts. **Git-ignored, never pushed** |

## Prometheus alert rules (`alert_rules.yml`)
| Alert | When |
|---|---|
| AppDown | the app's `/metrics` doesn't answer for 1 minute |
| HighCPU | CPU > 80% for 2 minutes |
| HighMemory | memory > 85% for 5 minutes |
| DiskAlmostFull | disk > 85% for 5 minutes |

## Commands
| Command | Meaning |
|---|---|
| `terraform plan` → `Plan: 4 to add, 2 to change, 0 to destroy` | preview: alarms, SNS, firewall ports, CPU credits |
| `terraform apply` | create them |
| `ansible-playbook site.yml` | install the monitoring stack: `ok=25 changed=16 failed=0` |
| `curl http://<server>:5000/metrics` | see the app's metrics as text |
| `http://<server>:9090/targets` | Prometheus: are all targets **UP**? |
| `http://<server>:9090/alerts` | Prometheus: which alerts are firing |
| `http://<server>:3000` | Grafana (first login `admin`/`admin`, then it forces a new password) |

**The stress test** (from the control node):
```bash
ansible web -m shell -a 'sleep $(( 300 - $(date +%s) % 300 )); timeout 300 sh -c "yes >/dev/null & yes >/dev/null & wait"' -B 700 -P 0
```
| Part | Meaning |
|---|---|
| `sleep $(( 300 - … ))` | wait for the next 5-minute mark, because CloudWatch averages in 5-minute blocks |
| `yes >/dev/null` ×2 | burn both CPU cores |
| `timeout 300` | stop after 5 minutes |
| `-B 700 -P 0` | run in the background, give my prompt back |

## Problems and lessons
**1. I first created `terraform.tfvars` with the example email**
- Fix: ran `Set-Content` again with my real email, checked with `Get-Content`

**2. CPU credits (t3 burstable instances)**
- A t3.micro only runs at 100% while it has **CPU credits**. Mine had ~8 credits = about 4–5 minutes at full speed.
- `standard` mode = when credits run out, the CPU slows down instead of charging money.
- So the test had to start **exactly** at a 5-minute mark to fill one CloudWatch block. It reached **80.9%**, just over 80.

**3. CloudWatch is slower than Prometheus**
- Free EC2 metrics come every **5 minutes**, Prometheus every **15 seconds**.
- Prometheus fired after 2 minutes, CloudWatch after about 4.5 minutes.
- Lesson: Prometheus for fast, detailed alerts. CloudWatch for "the whole server is down" alerts that work even if Prometheus itself is dead.

**4. Disk went from 42% to 77%**
- Grafana (635 MB) and Prometheus (386 MB) images plus the 1 GB swap file. Cleaned to 75% with `docker image prune`, `docker builder prune`, `apt-get clean`.
- Lesson: an 8 GB disk is too small for a real monitoring server. Prometheus storage is limited to 7 days / 1 GB.

**5. The alarm was already back to OK when I opened CloudWatch**
- That's normal: the stress test ended at 00:45 and the alarm recovered at 00:46. The **History** tab and the two emails show the full cycle.

## Screenshots
| File | Shows |
|---|---|
| `24-terraform-alarms-apply.png` | `Apply complete! 4 added, 2 changed` (account number hidden) |
| `25-ansible-monitoring-run.png` | playbook with the monitoring role: `failed=0` |
| `26-grafana-dashboard.png` | Grafana dashboard, everything OK |
| `27-prometheus-targets.png` | 3 targets UP |
| `28-grafana-cpu-spike.png` | stress test: CPU 100%, status CRITICAL |
| `29-prometheus-alert-firing.png` | HighCPU FIRING |
| `30-cloudwatch-alarm-email.png` | ALARM email: OK → ALARM, 80.9% > 80% |

## Interview line
"I added monitoring to my project. The app exposes a /metrics endpoint, and node_exporter adds Linux metrics. Prometheus scrapes them every 15 seconds and has alert rules, and Grafana shows a dashboard that's provisioned from files. Ansible deploys all of it as containers. On the AWS side, Terraform creates CloudWatch alarms for high CPU and failed status checks that email me through SNS. I tested it with a CPU stress test: Grafana went red, the Prometheus alert fired in 2 minutes, and I got the CloudWatch ALARM email and then the OK email when it recovered. I also set the t3 instance to standard CPU credits so a load test can never cost money."

## After the session
- Stop both servers (alarms use `notBreaching`, so a stopped server doesn't send alarm emails)
- Grafana password is saved on the server (Docker volume)
