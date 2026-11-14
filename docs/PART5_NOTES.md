# Part 5 Notes: Ansible (server setup from code)

## What we built
In Part 4, Terraform **created** the server, and a `user_data` script set it up **once** at first boot.
Now **Ansible** sets up the server from a playbook, and I can run it **any time, as many times as I like**.

```
Terraform  →  creates the server (infrastructure)
Ansible    →  sets up what runs on it (configuration)
GitHub Actions → deploys new code
```

**Result:**
| Run | PLAY RECAP | Meaning |
|---|---|---|
| 1st run | `ok=12 changed=7 failed=0` | Ansible set up the whole server |
| 2nd run | `ok=12 changed=0 failed=0` | **Idempotent**: nothing to fix, nothing touched |
| After I deleted the container | `ok=12 changed=1 failed=0` | **Self-healing**: it fixed only what was broken |

The dashboard footer shows `version ansible-73f524d`, so Ansible deployed that exact commit.

## Simple meanings
- **Ansible** = a free tool that connects to servers over **SSH** and makes them match a playbook. Nothing to install on the managed server (only Python, which Ubuntu already has)
- **Control node** = the computer that runs Ansible (my old console server)
- **Managed node** = the server Ansible sets up (the Terraform server)
- **Inventory** = the list of servers (`inventory.ini`)
- **Playbook** = a YAML file that says how the server should look (`site.yml`)
- **Task** = one step, like "install Docker"
- **Module** = the tool a task uses (`apt`, `service`, `git`, `cron`, `docker_container`...)
- **Role** = a folder that groups related tasks (`common`, `docker`, `app`, `cron`)
- **Idempotent** = running it again changes nothing if the server is already correct
- **ok (green)** = already correct; **changed (yellow)** = Ansible fixed it; **failed (red)** = error
- **Ad-hoc command** = a one-line Ansible command without a playbook
- **become (`-b`)** = run with sudo

## Network setup (why it's safe)
```
Control node (old server)  ──SSH, port 22, private IP 172.31.x.x──▶  Terraform server
```
- Terraform rule: SSH allowed **from the control node's security group**, not from an IP
  - a security group never changes, but a public IP changes on every restart
  - traffic stays **inside AWS** (private IPs), not over the internet
- `terraform plan` → `0 to add, 1 to change, 0 to destroy`, just one new firewall rule

## SSH key for Ansible
I **did not copy my laptop's private key** to another server.
The control node made **its own** key and only the **public** key was added to the Terraform server.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/ansible_key -N "" -C "ansible-control-node"
```
| Part | Meaning |
|---|---|
| `-t ed25519` | modern, strong key type |
| `-f ~/.ssh/ansible_key` | file name (private key + `.pub` public key) |
| `-N ""` | no passphrase, so Ansible can use it |
| `-C "..."` | a label so I know where the key came from |

The public key goes in the managed server's `~/.ssh/authorized_keys` (the list of keys allowed to log in).

## The `ansible/` folder
| File | What it does |
|---|---|
| `ansible.cfg` | settings: use `inventory.ini`, readable YAML output, pipelining (faster) |
| `inventory.ini` | `[web]` group: `health-monitor-tf` at its **private IP**, user `ubuntu`, key `~/.ssh/ansible_key` |
| `site.yml` | the playbook: apply 4 roles with sudo |
| `roles/common` | apt update, install git/curl/acl/python3-docker, timezone Asia/Kolkata |
| `roles/docker` | install Docker, start it on boot, add `ubuntu` to the docker group |
| `roles/app` | `git` pull → build image (only if the code changed) → run container → wait for `/healthz` |
| `roles/cron` | health check every 5 minutes |

## Commands (run on the control node)
| Command | Meaning |
|---|---|
| `sudo apt install -y ansible` | install Ansible (version 2.16) |
| `ansible --version` | check it's installed |
| `ansible all -i 172.31.3.0, -u ubuntu --private-key ~/.ssh/ansible_key -m ping` | test login. Answer `"ping": "pong"` |
| `cd ~/server-health-monitor && git pull` | get the latest playbook |
| `cd ansible` | always run Ansible **inside** the ansible folder (it reads `ansible.cfg` from there) |
| `ansible-playbook site.yml` | run the playbook |
| `ansible-playbook site.yml --check` | dry run: show what **would** change |
| `ansible web -b -a "docker rm -f health-monitor"` | ad-hoc command: delete the container (to test self-healing) |

## Ansible vs a Bash script
| Bash script / user_data | Ansible |
|---|---|
| runs every command every time | checks first, changes only what's different |
| run twice → may break or rebuild everything | run twice → `changed=0` |
| one server at a time | one command for 1 or 100 servers (add them to the inventory) |
| hard to read what it does | each task has a plain English name |

## Screenshots
| File | Shows |
|---|---|
| `18-terraform-ansible-rule.png` | plan: new SSH rule from the control node's security group |
| `19-ansible-ping.png` | first Ansible command: `"ping": "pong"` |
| `20-ansible-first-run.png` | 1st run: `changed=7` |
| `21-ansible-idempotent.png` | 2nd run: `changed=0` |
| `22-ansible-self-heal.png` | after deleting the container: `changed=1` |
| `23-dashboard-ansible.png` | dashboard footer: `version ansible-73f524d` |

## Interview line
"I used Ansible to configure my EC2 server. A control node in the same VPC connects over SSH using its own key, and the security group only allows SSH from the control node's security group, so nothing extra is open to the internet. The playbook has four roles: base packages, Docker, the app container with a health check, and a cron job. The first run made 7 changes, the second made 0, which shows it's idempotent. When I deleted the container, the next run recreated only that one thing."

## Next time
1. Part 5 LinkedIn post (best image: `21-ansible-idempotent.png`)
2. Part 6: Prometheus + Grafana + CloudWatch alerts
3. Decide: delete the old console server, or keep it as the Ansible control node

**Always:** stop both servers after the session.
