module "s3" {

    source = "./s3"
lambda_role_arn = module.lambda.lambda_role_arn
}


module "lambda" {
    source = "./lambda"
    aws_s3_bucket_arn =  module.s3.bucket_arn
 
    aws_s3_bucket_name = var.s3_bucket_name

  
}
