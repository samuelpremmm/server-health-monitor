# Part 6: AWS CloudWatch alarms that email me (through SNS) when the server has a problem.
# Basic EC2 metrics, up to 10 alarms and email notifications are inside the free tier.

resource "aws_sns_topic" "alerts" {
  name = "health-monitor-alerts"
}

# AWS sends a "Confirm subscription" email first. Alerts only arrive after I click it.
resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CPU above 80% (average over 5 minutes)
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "health-monitor-high-cpu"
  alarm_description   = "CPU above 80% on health-monitor-tf"
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = { InstanceId = aws_instance.health_monitor.id }
  statistic           = "Average"
  period              = 300 # basic monitoring sends data every 5 minutes (free)
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  treat_missing_data  = "notBreaching" # a stopped server is not an alarm
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn] # also email when it's back to normal
}

# The server failed an AWS health check (hardware or the OS stopped responding)
resource "aws_cloudwatch_metric_alarm" "status_check" {
  alarm_name          = "health-monitor-status-check-failed"
  alarm_description   = "EC2 status check failed on health-monitor-tf"
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed"
  dimensions          = { InstanceId = aws_instance.health_monitor.id }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}
