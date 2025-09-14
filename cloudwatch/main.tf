resource "aws_sns_topic" "lambda_alerts" {
  name = "book-lambda-alerts"
}

resource "aws_sns_topic_subscription" "lambda_alerts_email" {
  topic_arn = aws_sns_topic.lambda_alerts.arn
  protocol  = "email"
  endpoint  = "amritpoudel433@gmail.com"
}

resource "aws_cloudwatch_metric_alarm" "lambda_error_alarm" {
  for_each = toset(var.lambda_names)

  alarm_name          = "nepse-${each.key}-error-alarm"
  alarm_description   = "Alarm when ${each.key} Lambda has errors > 0"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 60   # 1 minute interval
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.key
  }

  alarm_actions = [aws_sns_topic.lambda_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_memory_alarm" {
  for_each = toset(var.lambda_names)

  alarm_name          = "nepse-${each.key}-memory-alarm"
  alarm_description   = "Alarm when ${each.key} Lambda memory usage exceeds 80%"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "MaxMemoryUsed"
  namespace           = "AWS/Lambda"
  period              = 60   # 1 minute interval
  statistic           = "Maximum"
  threshold           = 80 * 1024 * 1024  # 80% of 128 MB memory (adjust if needed)
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = each.key
  }

  alarm_actions = [aws_sns_topic.lambda_alerts.arn]
}


resource "aws_cloudwatch_metric_alarm" "s3_bucket_size_alarm" {
  alarm_name          = "s3-bucket-size-alarm"
  alarm_description   = "Alarm if S3 bucket exceeds 10 GB"
  namespace           = "AWS/S3"
  metric_name         = "BucketSizeBytes"
  dimensions = {
    BucketName  = "amrit-s3-bucket-lf"
    StorageType = "StandardStorage"
  }
  statistic           = "Average"
  period              = 86400     
  evaluation_periods  = 1
  threshold           = 100 * 1024 * 1024
  comparison_operator = "GreaterThanThreshold"
  alarm_actions       = [aws_sns_topic.lambda_alerts.arn]
}
