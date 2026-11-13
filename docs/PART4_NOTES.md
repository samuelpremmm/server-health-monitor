# Part 4 Notes: Terraform (server from code)

## What we built
Before, I created my server by **clicking in the AWS console**.
Now I **write the server as code**, and Terraform creates it for me.

```
terraform apply    →  creates EC2 + security group + SSH key   (~1 min)
terraform destroy  →  deletes all of it                         (~1 min)
```

**Result:** I destroyed my whole server and rebuilt it from code. **Zero → working dashboard in 93 seconds.**
No console clicks, no MobaXterm.

## Simple meanings
- **Terraform** = a free tool that reads `.tf` files and creates cloud resources from them
- **Infrastructure as Code (IaC)** = servers, firewalls and keys written as code, so they can be saved in Git, reviewed and rebuilt any time
- **Provider** = Terraform's plugin for a cloud (`hashicorp/aws` talks to AWS)
- **Resource** = one thing Terraform creates (EC2 instance, security group, key pair)
- **Data source** = something Terraform only **reads** (latest Ubuntu image, my IP)
- **State file (`terraform.tfstate`)** = Terraform's memory of what it created. It can contain sensitive details, so **never push it to GitHub** (it's in `.gitignore`)
- **Plan** = a preview of what will change. **Nothing is created at the plan step.**
- **user_data** = a script AWS runs **once** when the server first boots
- **IAM user** = a separate login for tools, so I never use root keys
- **Access key** = the password the AWS CLI / Terraform uses to talk to my account

## Who does what
| Tool | Used for |
|---|---|
| **AWS console (Chrome)** | Create the IAM user + access key (one time) |
| **Command Prompt** | `aws configure`, `terraform` commands |
| **Terraform** | Creates / deletes the server, firewall and key |
| **user_data.sh** | On first boot: installs Docker and starts the dashboard |

## Step 1: IAM user + access key (AWS console)
1. IAM → **IAM users** → **Create user** → name `devops-admin`
2. **Attach policies directly** → `AdministratorAccess` → Create user
3. devops-admin → **Security credentials** → **Create access key** → **CLI** → Create
4. Download the `.csv` file (keep it private)

**Never create access keys for the root user.**

## Step 2: Connect my laptop to AWS (cmd)
| Command | Meaning |
|---|---|
| `aws configure` | Save my access key, region (`ap-south-1`) and output format (`json`) on my laptop |
| `aws sts get-caller-identity` | "Who am I?" Shows `user/devops-admin` if it works |

## Step 3: The Terraform files (`terraform/` folder)
| File | What it does |
|---|---|
| `providers.tf` | Use AWS in Mumbai; tag everything `ManagedBy = terraform` |
| `variables.tf` | Settings: region, `t3.micro`, SSH key path, repo URL |
| `security.tf` | Finds **my IP automatically**, opens **22** and **5000** to that IP **/32 only** |
| `main.tf` | EC2: Ubuntu 24.04, t3.micro, **8 GB encrypted** disk, **IMDSv2** |
| `user_data.sh` | First boot: install Docker + Git, clone repo, `docker build`, `docker run` |
| `outputs.tf` | Prints the public IP, dashboard URL and SSH command |

**SSH key:** made with `ssh-keygen -t ed25519 -f ~/.ssh/health-monitor-tf`
- private key stays on my laptop, the `.pub` key is uploaded by Terraform

## Step 4: Terraform commands
| Command | Meaning |
|---|---|
| `terraform init` | Download the AWS plugin (run once per folder) |
| `terraform fmt` | Tidy the code formatting |
| `terraform validate` | Check the code has no mistakes |
| `terraform plan` | **Preview** what will be created / changed / deleted |
| `terraform apply` | **Create** what the plan showed |
| `terraform output` | Show the IP / URL again |
| `terraform state list` | List what Terraform is managing |
| `terraform plan -destroy` | Preview what destroy would delete |
| `terraform destroy` | **Delete** everything Terraform created |

`cd /d "C:\...\server-health-monitor\terraform"` → always run terraform **inside** the terraform folder.

## Terraform in action (what happened today)
```
terraform plan     →  Plan: 3 to add, 0 to change, 0 to destroy
terraform apply    →  key pair 1s, security group 3s, instance 13s
                      Apply complete! Resources: 3 added
(wait ~45s)        →  user_data installs Docker, dashboard is UP: {"status": "ok"}

terraform destroy  →  instance 40s, key 0s, SG 1s
                      Resources: 3 destroyed   (took 71s)
terraform apply    →  Resources: 3 added
                      dashboard UP again       (total 93s)

terraform plan     →  No changes. Your infrastructure matches the configuration.
```
In the EC2 console I could see all three: old server **Stopped**, destroyed one **Terminated**, rebuilt one **Running 3/3 checks**.

## Security habits
- `terraform plan` first, check it, then `apply` / `destroy`
- Security group: my IP `/32` only, never `0.0.0.0/0` for SSH
- Disk encrypted, IMDSv2 required
- State, plan and `.tfvars` files are git-ignored
- Only free-plan resources: no Elastic IP, NAT gateway or load balancer

## Errors and fixes

**1. AWS CLI: "Unable to locate credentials"**
- Why: the laptop was not connected to AWS yet
- Fix: create an access key for `devops-admin`, run `aws configure`

**2. IAM showed 0 users**
- Why: `devops-admin` had never been created
- Fix: IAM → Create user → `AdministratorAccess`

**3. I leaked my secret key in a screenshot** ⚠️
- Why: I screenshotted the `aws configure` screen
- Fix (**key rotation**): create a new key → `aws configure` with the new key → deactivate + delete the old key
- Lesson: never screenshot keys, passwords, tokens or `.pem` files

**4. "The security token included in the request is invalid"**
- Why: the old key was deleted before the new one was configured
- Fix: run `aws configure` with the new key

## Interview line
"I wrote my AWS infrastructure in Terraform: an EC2 instance with an encrypted disk and IMDSv2, a security group that allows only my IP, and an SSH key pair. A user_data script installs Docker and starts the app on first boot. I proved it's reproducible by running terraform destroy and apply: the whole server came back healthy in 93 seconds. I also rotated an access key after accidentally exposing it."

## Next time
1. Start / apply the server → check the dashboard
2. Part 4 LinkedIn post (best image: `16-ec2-terraform-tags.png`)
3. Part 5: Ansible (set up the server automatically, including the GitHub runner)
4. Delete the old console server (only after the new one does everything)

**Always:** stop or destroy the instance after the session.
