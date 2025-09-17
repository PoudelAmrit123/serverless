module "s3" {

    source = "./s3"
# lambda_role_arn = module.lambda.lambda_role_arn
codebuild_iam_role_arn = module.cicd.codebuild_iam_role_arn
data_analyzer_lambda_arn = module.lambda.data_analyzer_lambda_arn 
data_ingestor_lambda_arn = module.lambda.data_analyzer_lambda_arn 
notifier_lambda_arn = module.lambda.notifier_lambda_role_arn

}


module "lambda" {
    source = "./lambda"
    aws_s3_bucket_arn =  module.s3.bucket_arn
 
    aws_s3_bucket_name = var.s3_bucket_name

  
}

module "eventbridge" {
  source = "./event_bridge"
  lambda_function_arn =  module.lambda.data_analyzer_function_arn
  lambda_function_name = module.lambda.data_analyzer_function_function_name 
  notifier_lambda_arn = module.lambda.notifier_lambda_arn
  notifier_lambda_name = module.lambda.notifier_lambda_name

}

module "dynamodb" {
  source = "./dynamoDb"
  
}

module "ses" {
  source = "./SES" 
}

module "cicd" {
  source = "./ci-cd" 
  backend_bucket_arn =   module.s3.backend_bucket_arn
  s3_main_bucket_arn = module.s3.bucket_arn   
  # cloudwatch_lambda_error_alarm_arn =  module.cloudwatch.cloudwatch_lambda_error_alarm_arn
  # cloudwatch_lambda_memory_alarm_arn = module.cloudwatch.cloudwatch_lambda_memory_alarm_arn 
  # cloudwatch_s3_bucket_size_alarm_arn = module.cloudwatch.cloudwatch_s3_bucket_size_alarm_arn 
  sns_topic_arn = module.cloudwatch.sns_topic_arn
  ses_email_primary = module.ses.ses_primary
  ses_email_secondary = module.ses.ses_secondary 
  notifier_rule = module.eventbridge.notifier_lambda_arn
  s3_processed_rule = module.eventbridge.notifier_s3_arn

}

module "cloudwatch" {
  source = "./cloudwatch"
  
}