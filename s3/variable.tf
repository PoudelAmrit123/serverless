# variable "lambda_role_arn" {
#     description = "lambda role attached to lambda function arn for the s3 bucket policy."
#     type = string
  
# }
variable "data_ingestor_lambda_arn" {
    type = string
  
}

variable "data_analyzer_lambda_arn" {
    type = string
  
}

variable "notifier_lambda_arn" {
    type = string
  
}
variable "codebuild_iam_role_arn" {
    description = "codebuild iam role arn"
    type = string
  
}