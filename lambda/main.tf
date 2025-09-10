## Creating the Lambda Function 


resource "aws_lambda_layer_version" "lambda_layer" {
  filename            = "${path.module}/layer.zip"
  layer_name          = "lambda_layer_dependencies_layer"
  description         = "Common dependencies for Lambda functions"
  compatible_runtimes = ["python3.12"]

  compatible_architectures = ["x86_64"]
}

                 ## Data Ingestor Function

data "archive_file" "data_ingestor_archive" {
  type        = "zip"
  source_file = "${path.module}/boto3/data_ingestor_lambda.py"

  output_path = "${path.module}/boto3/data_ingestor_lambda.zip"
}



resource "aws_lambda_function" "data_ingestor_function" {
  filename         = data.archive_file.data_ingestor_archive.output_path
  source_code_hash = data.archive_file.data_ingestor_archive.output_base64sha256
  function_name = "data_ingestor_function"
  role          = aws_iam_role.lambda_iam_role.arn
  handler = "data_ingestor_lambda.lambda_handler"

  runtime       = "python3.12"

   memory_size = 1024     # Increase memory (try 1024 MB or 2048 MB)
  timeout     = 900      # Max = 900 seconds (15 minutes)

  layers = [aws_lambda_layer_version.lambda_layer.arn]

#   tracing_config {
#     mode = "Active" # Enable X-Ray tracing
#   }
}


####################################################

#                  ## Data Analyzer Function 

data "archive_file" "data_analyzer_archive" {
  type        = "zip"
  source_file = "${path.module}/boto3/data_analyzer_lambda.py"
  output_path = "${path.module}/boto3/data_analyzer_lambda.zip"
}



resource "aws_lambda_function" "data_analyzer_function" {
   filename         = data.archive_file.data_analyzer_archive.output_path
  source_code_hash = data.archive_file.data_analyzer_archive.output_base64sha256
  function_name = "data_analyzer_function"
  role          = aws_iam_role.lambda_iam_role.arn
  handler       = "data_analyzer_lambda.lambda_handler"
  runtime       = "python3.12"

   memory_size = 1024     # Increase memory (try 1024 MB or 2048 MB)
  timeout     = 900      # Max = 900 seconds (15 minutes)

  # layers = [aws_lambda_layer_version.lambda_layer.arn]

#   tracing_config {
#     mode = "Active" # Enable X-Ray tracing
#   }
}

#            ## Notifier Function


# data "archive_file" "notifier_archive" {
#   type        = "zip"
#   source_file = "${path.module}/boto3/notifier_lambda.py"
#   output_path = "${path.module}/boto3/notifier_lambda.zip"
# }



# resource "aws_lambda_function" "notifier_function" {
#  filename         = data.archive_file.notifier_archive.output_path
#   source_code_hash = data.archive_file.notifier_archive.output_base64sha256
#   function_name = "notifier_function"
#   role          = aws_iam_role.lambda_iam_role.arn
#   handler       = "notifier_lambda.lambda_handler"
#   runtime       = "python3.12"

#   layers = [aws_lambda_layer_version.lambda_layer.arn]

# #   tracing_config {
# #     mode = "Active" # Enable X-Ray tracing
# #   }
# }

###############################################


## Lambda Role 
## Later Move the different permission per lambda function.


resource "aws_iam_role" "lambda_iam_role" {
    name = "lambda_role"

     assume_role_policy = jsonencode({
  Version: "2012-10-17",
  Statement: [
    {
      Effect: "Allow",
      Action: "sts:AssumeRole",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    
    }
  ]
})  
}


# TODO: Replace bucket name. 
resource "aws_iam_policy" "iam_policy" {
  name = "iam_role_policy_s3"
  policy = jsonencode({
    Version: "2012-10-17",
    Statement: [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource = [
          "${var.aws_s3_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket"
        ],
        Resource = [
          "${var.aws_s3_bucket_arn}"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "bedrock:InvokeModel"
        ],
        Resource = "*"
      } ,
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ],
        Resource = "arn:aws:dynamodb:us-east-1:702865854817:table/BedrockResults"
      }
    ]
  })
}


resource "aws_iam_role_policy_attachment" "iam_role_policy_attachment" {
    policy_arn = aws_iam_policy.iam_policy.arn 
    role = aws_iam_role.lambda_iam_role.name
  

}

# Allow Lambda to create log groups/streams & put logs
resource "aws_iam_role_policy_attachment" "lambda_logging" {
  role       = aws_iam_role.lambda_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}





### Lambda Trigger... 

## Triggering while data ingestor lambda while uploading the data. 
## upload the good one to processed/ and failure to rejects/

resource "aws_lambda_permission" "s3_data_ingestor" {
    statement_id = "AllowS3InvokeIngestor"
    action = "lambda:InvokeFunction"
    function_name = aws_lambda_function.data_ingestor_function.function_name
    principal = "s3.amazonaws.com"
    source_arn = var.aws_s3_bucket_arn
  
}

resource "aws_s3_bucket_notification" "upload_trigger" {
bucket =  var.aws_s3_bucket_name 


lambda_function {
       lambda_function_arn = aws_lambda_function.data_ingestor_function.arn
       filter_prefix = "upload/"
       events = [ "s3:ObjectCreated:*" ]  
}
  depends_on = [aws_lambda_permission.s3_data_ingestor]

  eventbridge = true
}





  

#   #################################################

# ## Triggered while the data is uploaded to processed/ 

#   resource "aws_lambda_permission" "s3_data_analyzer" {
#     statement_id = "AllowS3InvokeIngestor"
#     action = "lambda:InvokeFunction"
#     function_name = aws_lambda_function.data_analyzer_function.function_name
#     principal = "s3:amazonaws.com"
#     source_arn = var.aws_s3_bucket_arn
  
# }

# resource "aws_s3_bucket_notification" "bedrock_trigger" {
# bucket =  var.aws_s3_bucket_name

# lambda_function {
#        lambda_function_arn = aws_lambda_function.data_analyzer_function.arn
#        filter_prefix = "processed/"
#        events = [ "s3:ObjectCreated:*" ]
# }
# }

# #############################################

## Triggered for notification 
## Triggered After the DynamoDB database is filled. 

# (the logic is changed to EVENT BRIDGE)












