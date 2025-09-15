output "sns_topic_arn" {
    value = aws_sns_topic.lambda_alerts.arn
  
}

# output "cloudwatch_lambda_error_alarm_arn" {
#     value = aws_cloudwatch_metric_alarm.lambda_error_alarm.arn
  
# }


output "cloudwatch_lambda_error_alarm_arns" {
  description = "ARNs of all Lambda error alarms"
  value = { for k, a in aws_cloudwatch_metric_alarm.lambda_error_alarm : k => a.arn }
}


# output "cloudwatch_lambda_memory_alarm_arn" {
#     value = aws_cloudwatch_metric_alarm.lambda_memory_alarm.arn
  
# }

output "cloudwatch_lambda_memory_alarm_arns" {
  description = "ARNs of all Lambda memory alarms"
  value = { for k, a in aws_cloudwatch_metric_alarm.lambda_memory_alarm : k => a.arn }
}


output "cloudwatch_s3_bucket_size_alarm_arn" {
    value = aws_cloudwatch_metric_alarm.s3_bucket_size_alarm.arn
  
}