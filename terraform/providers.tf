# Which tools Terraform needs, and which AWS region to use.

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws" # talks to AWS
      version = "~> 6.0"
    }
    http = {
      source  = "hashicorp/http" # used to find my laptop's public IP
      version = "~> 3.4"
    }
  }
}

provider "aws" {
  region = var.region

  # Every resource gets these tags, so I can see in the console what Terraform made
  default_tags {
    tags = {
      Project   = "server-health-monitor"
      ManagedBy = "terraform"
    }
  }
}
