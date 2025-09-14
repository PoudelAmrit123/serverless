variable "lambda_role_arn" {
    description = "lambda role attached to lambda function arn for the s3 bucket policy."
    type = string
  
}

variable "codebuild_iam_role_arn" {
    description = "codebuild iam role arn"
    type = string
  
}