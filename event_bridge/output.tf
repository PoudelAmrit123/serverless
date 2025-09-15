output "notifier_lambda_arn" {
    value = aws_cloudwatch_event_rule.notifier_rule.arn
  
}

output "notifier_s3_arn" {
    value = aws_cloudwatch_event_rule.s3_processed_rule.arn
  
}