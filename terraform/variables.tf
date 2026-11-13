# Settings I can change without touching the rest of the code.

variable "region" {
  description = "AWS region (Mumbai)"
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "EC2 size. t3.micro is covered by the free plan"
  type        = string
  default     = "t3.micro"
}

variable "public_key_path" {
  description = "My SSH public key (the private key never leaves my laptop)"
  type        = string
  default     = "~/.ssh/health-monitor-tf.pub"
}

variable "repo_url" {
  description = "Git repo the server clones and runs"
  type        = string
  default     = "https://github.com/samuelpremmm/server-health-monitor.git"
}
