# Part 3 Notes: CI/CD (auto deploy on git push)

## What we built
Now when I **push code to GitHub**, it is **tested and deployed to my EC2 server automatically**.
I don't log in to the server to deploy any more.

```
git push  →  GitHub Actions  →  run tests  →  build Docker image  →  replace container on EC2  →  check /healthz
```

## Simple meanings
- **CI (Continuous Integration)** = every push is tested automatically (flake8 + pytest)
- **CD (Continuous Deployment)** = if tests pass, the new code goes live automatically
- **GitHub Actions** = GitHub's tool that runs these steps. The steps are written in a YAML file: `.github/workflows/python-app.yml`
- **Workflow** = the full list of steps. **Job** = one group of steps (`build`, `deploy`)
- **Runner** = the computer that runs a job
  - `build` runs on **GitHub's** computer (free)
  - `deploy` runs on **my EC2** (self-hosted runner)
- **Self-hosted runner** = a small program on my EC2 that **connects out** to GitHub and asks "any job for me?"
  - So I did **not** open any new port. The security group is still locked to my IP.
- **Registration token** = a one-time password from GitHub to connect the runner. It expires in 1 hour. Never share it publicly.

## Who does what
| Tool | Used for |
|---|---|
| **MobaXterm** | Only **once**: to install the runner on EC2 |
| **GitHub website** | Create the runner token, watch the **Actions** tab |
| **Laptop / GitHub edit** | Change code and `git push` → this starts the deploy |

## Step 1: Install the runner on EC2 (MobaXterm, one time only)

| Command | Meaning |
|---|---|
| `cd ~` | Go to the home folder |
| `mkdir actions-runner && cd actions-runner` | Make a folder for the runner and go inside |
| `curl -o runner.tar.gz -L <link>` | Download the runner program |
| `tar xzf runner.tar.gz` | Unpack (unzip) it |
| `./config.sh --url <repo-link> --token <token>` | Connect the runner to my GitHub repo |
| `sudo ./svc.sh install` | Make it a systemd service |
| `sudo ./svc.sh start` | Start it now (and at every boot) |
| `sudo ./svc.sh status` | Check it is **active (running)** |

`config.sh` questions: runner group → **Enter**, name → (I got **self hosted**), labels → **Enter**, work folder → **Enter** (`_work`)

## Step 2: Security (GitHub settings)
**Settings → Actions → General → "Require approval for all external contributors"**
- Why: my repo is public. Without this, a stranger's pull request could run code on **my** server.
- Also, the deploy job runs **only on push to main**, never for pull requests.

## Step 3: The deploy job (what it does on EC2)
| Step in workflow | Command it runs | Meaning |
|---|---|---|
| Checkout | `actions/checkout` | Get the latest code |
| Build image | `docker build -t health-monitor:latest .` | Make a new image from the new code |
| Replace container | `docker rm -f health-monitor` then `docker run -d ...` | Delete the old container, start the new one |
| Health check | `curl -fsS http://127.0.0.1:5000/healthz` | Check the app answers. If not → ❌ red |
| Clean up | `docker image prune -f` | Delete old unused images (save disk) |

`needs: build` = deploy waits for the tests. **Tests fail → no deploy.**

## How I deploy now (every time)
```
# on my laptop
git add .
git commit -m "my change"
git push
```
Or edit a file on GitHub website → **Commit changes**.
Then open **GitHub → Actions** → watch **build ✅ → deploy ✅**.
The dashboard footer shows the new **version** (commit ID) = proof it was deployed.

## Testing I did
| Test | Command / place | Pass when |
|---|---|---|
| Dashboard | `http://<ip>:5000` | Page loads, footer shows version |
| Container | `docker ps` | `health-monitor (healthy)` |
| Runner service | `sudo systemctl status actions.runner.* --no-pager` | active (running) |
| App alive | `curl http://localhost:5000/healthz` | `{"status": "ok"}` |
| Runner online | GitHub → Settings → Actions → Runners | **Idle** 🟢 |
| Real deploy | Edited README on GitHub | Version changed by itself |
| Reboot | `sudo reboot` then `docker ps` | Container is back by itself |

## Errors and fixes

**1. 404 Not Found when running config.sh**
- Why: I used an example token (`AB12...`), not my real one
- Fix: copy the real command from GitHub → Settings → Actions → Runners → **New self-hosted runner**

**2. `sudo: ./svc.sh: command not found`**
- Why: `svc.sh` is created **only after** `config.sh` succeeds
- Fix: run `config.sh` first, wait for **Settings Saved**, then `svc.sh`

**3. `config.cmd` instead of `config.sh`**
- Why: **Windows** was selected on the GitHub page. `.cmd` = Windows, `.sh` = Linux
- Fix: select **Linux**, use `./config.sh`

**4. Runner label `ec2` missing**
- Why: I pressed Enter at the labels question
- Fix: changed the workflow to `runs-on: [self-hosted, Linux, X64]`

## Interview line
"I built a CI/CD pipeline with GitHub Actions. Every push to main runs flake8 and pytest. If they pass, a self-hosted runner on my EC2 server rebuilds the Docker image, replaces the container and checks a /healthz endpoint. I used a self-hosted runner so I didn't have to open SSH to the internet, and I required approval for fork pull requests because the repo is public."

## Next time
1. Start EC2 → check my IP in the security group (runner + container start by themselves)
2. Screenshots: Actions run (build → deploy) + dashboard footer with version
3. Write the Part 3 LinkedIn post
4. Part 4: Terraform (create the server with code)

**Always:** stop the EC2 instance after the session.
