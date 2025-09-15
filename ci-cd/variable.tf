variable "backend_bucket_arn" {
    description = "backend bucekt"
   type = string
  
}

variable "s3_main_bucket_arn" {
    description = "s3 main bucket arn"
    type = string
  
}

variable "sns_topic_arn" {
    type = string
  
}

# variable "cloudwatch_lambda_error_alarm_arn" {
#     type = string
  
# }

# variable "cloudwatch_lambda_memory_alarm_arn" {
#     type = string
  
# }

# variable "cloudwatch_s3_bucket_size_alarm_arn" {
#     type = string
  
# }

variable "ses_email_primary" {
    type = string
  
}
variable "ses_email_secondary" {
    type = string
  
}

variable "s3_processed_rule" {
    type = string
  
}

variable "notifier_rule" {
    type = string
  
}