output "sns_topic_arn" {
    value = aws_sns_topic.lambda_alerts.arn
  
}

output "cloudwatch_lambda_error_alarm_arn" {
    value = aws_cloudwatch_metric_alarm.lambda_error_alarm.arn
  
}

output "cloudwatch_lambda_memory_alarm_arn" {
    value = aws_cloudwatch_metric_alarm.lambda_memory_alarm.arn
  
}

output "cloudwatch_s3_bucket_size_alarm_arn" {
    value = aws_cloudwatch_metric_alarm.s3_bucket_size_alarm.arn
  
}