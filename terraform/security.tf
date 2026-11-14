# Firewall for the server: only MY IP can reach SSH (22) and the dashboard (5000).

# Ask AWS "what is my public IP?" so I never type it by hand (and never commit it)
data "http" "my_ip" {
  url = "https://checkip.amazonaws.com"
}

locals {
  my_ip_cidr = "${chomp(data.http.my_ip.response_body)}/32" # /32 = exactly one IP
}

resource "aws_security_group" "health_monitor" {
  name        = "health-monitor-tf-sg"
  description = "SSH and dashboard from my IP only"

  ingress {
    description = "SSH from my IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.my_ip_cidr]
  }

  ingress {
    description = "Dashboard from my IP"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = [local.my_ip_cidr]
  }

  # Part 5: the Ansible control node may SSH in over AWS's private network.
  # It points at the control node's security group, not an IP, so nothing opens to the internet.
  dynamic "ingress" {
    for_each = var.ansible_control_sg_id == "" ? [] : [var.ansible_control_sg_id]
    content {
      description     = "SSH from Ansible control node"
      from_port       = 22
      to_port         = 22
      protocol        = "tcp"
      security_groups = [ingress.value]
    }
  }

  egress {
    description = "Server can reach the internet (apt, GitHub, Docker Hub)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "health-monitor-tf-sg" }
}
