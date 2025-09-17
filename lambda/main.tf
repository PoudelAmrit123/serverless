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
  role          = aws_iam_role.data_ingestor_role.arn
  handler = "data_ingestor_lambda.lambda_handler"

  runtime       = "python3.12"

   memory_size = 1024     
  timeout     = 900     

  layers = [aws_lambda_layer_version.lambda_layer.arn]


   }


####################################################

 ## Data Analyzer Function 

data "archive_file" "data_analyzer_archive" {
  type        = "zip"
  source_file = "${path.module}/boto3/data_analyzer_lambda.py"
  output_path = "${path.module}/boto3/data_analyzer_lambda.zip"
}



resource "aws_lambda_function" "data_analyzer_function" {
   filename         = data.archive_file.data_analyzer_archive.output_path
  source_code_hash = data.archive_file.data_analyzer_archive.output_base64sha256
  function_name = "data_analyzer_function"
  role          = aws_iam_role.data_analyzer_role.arn
  handler       = "data_analyzer_lambda.lambda_handler"
  runtime       = "python3.12"

   memory_size = 1024     
  timeout     = 900     


   }

## Notifier Function


data "archive_file" "notifier_archive" {
  type        = "zip"
  source_file = "${path.module}/boto3/notifier_lambda.py"
  output_path = "${path.module}/boto3/notifier_lambda.zip"
}



resource "aws_lambda_function" "notifier_function" {
 filename         = data.archive_file.notifier_archive.output_path
  source_code_hash = data.archive_file.notifier_archive.output_base64sha256
  function_name = "notifier_function"
  role          = aws_iam_role.notifier_role.arn
  handler       = "notifier_lambda.lambda_handler"
  runtime       = "python3.12"


  }

###############################################

# TODO: change the lambda function to separate three different 
## Lambda Role 
## Later Move the different permission per lambda function.


# resource "aws_iam_role" "lambda_iam_role" {
#     name = "lambda_role"

#      assume_role_policy = jsonencode({
#   Version: "2012-10-17",
#   Statement: [
#     {
#       Effect: "Allow",
#       Action: "sts:AssumeRole",
#       Principal = {
#         Service = "lambda.amazonaws.com"
#       }
    
#     }
#   ]
# })  
# }


### Role for the lambda
resource "aws_iam_role" "data_ingestor_role" {
    name = "data_ingestor_lambda_role"

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

resource "aws_iam_role" "data_analyzer_role" {
  name = "data_analyzer_lambda_role"

  assume_role_policy = jsonencode({
    Version: "2012-10-17",
    Statement: [{
      Effect = "Allow",
      Action = "sts:AssumeRole",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role" "notifier_role" {
  name = "notifier_lambda_role"

  assume_role_policy = jsonencode({
    Version: "2012-10-17",
    Statement: [{
      Effect = "Allow",
      Action = "sts:AssumeRole",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}


### Data ingestor policy 

resource "aws_iam_policy" "data_ingestor_policy" {
  name = "data_ingestor_policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
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
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_data_ingestor" {
  policy_arn = aws_iam_policy.data_ingestor_policy.arn
  role       = aws_iam_role.data_ingestor_role.name
}


## data analyzer role policy

resource "aws_iam_policy" "data_analyzer_policy" {
  name = "data_analyzer_policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
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
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ],
        Resource = "arn:aws:dynamodb:us-east-1:702865854817:table/BedrockResults"
      },

      {
        Effect = "Allow",
        Action = "events:PutEvents",
        Resource = "*"
      } 
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_data_analyzer" {
  policy_arn = aws_iam_policy.data_analyzer_policy.arn
  role       = aws_iam_role.data_analyzer_role.name
}


## Notifer role 


resource "aws_iam_policy" "notifier_policy" {
  name = "notifier_policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
       {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ],
        Resource = "arn:aws:dynamodb:us-east-1:702865854817:table/BedrockResults"
      },

      {
        Effect = "Allow",
        Action = "events:PutEvents",
        Resource = "*"
      } ,
       {
        Effect   = "Allow"
        Action   = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        # Resource = "arn:aws:ses:us-east-1:${data.aws_caller_identity.current.account_id}:identity/officalamritpoudel433@gmail.com"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_notifier_policy" {
  policy_arn = aws_iam_policy.notifier_policy.arn
  role       = aws_iam_role.notifier_role.name
}






# # TODO: Replace bucket name. 
# resource "aws_iam_policy" "iam_policy" {
#   name = "iam_role_policy_s3"
#   policy = jsonencode({
#     Version: "2012-10-17",
#     Statement: [
#       {
#         Effect = "Allow",
#         Action = [
#           "s3:GetObject",
#           "s3:PutObject"
#         ],
#         Resource = [
#           "${var.aws_s3_bucket_arn}/*"
#         ]
#       },
#       {
#         Effect = "Allow",
#         Action = [
#           "s3:ListBucket"
#         ],
#         Resource = [
#           "${var.aws_s3_bucket_arn}"
#         ]
#       },
#       {
#         Effect = "Allow",
#         Action = [
#           "bedrock:InvokeModel"
#         ],
#         Resource = "*"
#       } ,
#       {
#         Effect = "Allow",
#         Action = [
#           "dynamodb:PutItem",
#           "dynamodb:GetItem",
#           "dynamodb:UpdateItem"
#         ],
#         Resource = "arn:aws:dynamodb:us-east-1:702865854817:table/BedrockResults"
#       },

#       {
#         Effect = "Allow",
#         Action = "events:PutEvents",
#         Resource = "*"
#       } ,

#        {
#         Effect   = "Allow"
#         Action   = [
#           "ses:SendEmail",
#           "ses:SendRawEmail"
#         ]
#         # Resource = "arn:aws:ses:us-east-1:${data.aws_caller_identity.current.account_id}:identity/officalamritpoudel433@gmail.com"
#         Resource = "*"
#       }
#     ]
#   })
# }


# resource "aws_iam_role_policy_attachment" "iam_role_policy_attachment" {
#     policy_arn = aws_iam_policy.iam_policy.arn 
#     role = aws_iam_role.lambda_iam_role.name
  

# }

# Allow Lambda to create log groups/streams & put logs
resource "aws_iam_role_policy_attachment" "lambda_logging_data_analyzer" {
  role       = aws_iam_role.data_analyzer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_logging_data_ingestor" {
  role       = aws_iam_role.data_ingestor_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_logging_notifier" {
  role       = aws_iam_role.notifier_role.name
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
       filter_prefix = "input/"
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












