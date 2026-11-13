# Printed at the end of `terraform apply`.

output "public_ip" {
  description = "Server public IP (changes if the instance is stopped and started)"
  value       = aws_instance.health_monitor.public_ip
}

output "dashboard_url" {
  value = "http://${aws_instance.health_monitor.public_ip}:5000"
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/health-monitor-tf ubuntu@${aws_instance.health_monitor.public_ip}"
}
