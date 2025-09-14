module "s3" {

    source = "./s3"
lambda_role_arn = module.lambda.lambda_role_arn
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
}