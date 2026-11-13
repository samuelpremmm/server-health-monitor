# The server itself.

# Find the latest official Ubuntu 24.04 image (published by Canonical)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

# Upload my SSH public key to AWS so I can log in with MobaXterm
resource "aws_key_pair" "health_monitor" {
  key_name   = "health-monitor-tf-key"
  public_key = file(pathexpand(var.public_key_path))
}

resource "aws_instance" "health_monitor" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.health_monitor.key_name
  vpc_security_group_ids = [aws_security_group.health_monitor.id]

  # Runs once on first boot: installs Docker and starts the dashboard
  user_data = templatefile("${path.module}/user_data.sh", {
    repo_url = var.repo_url
  })

  root_block_device {
    volume_size = 8 # GB, inside the free plan
    volume_type = "gp3"
    encrypted   = true # disk is encrypted at rest
  }

  metadata_options {
    http_tokens = "required" # IMDSv2 only (AWS security best practice)
  }

  tags = { Name = "health-monitor-tf" }
}
