resource "aws_s3_bucket" "s3_bucket" {

    bucket = "amrit-s3-bucket-lf"
    force_destroy = true

    tags = {
      Name = "Amrit" ,
      Project = "Assignment"
    }
  
}


## Enabling the Versionig

resource "aws_s3_bucket_versioning" "aws_s3_bucket_versioning" {
    bucket = aws_s3_bucket.s3_bucket.id
    versioning_configuration {
      status = "Enabled"
    }
  
}

## Enabling the encryption

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_encryption" {
    bucket = aws_s3_bucket.s3_bucket.id
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }

  
}

## Bucket for backned 


resource "aws_s3_bucket" "s3_backend_bucket" {

    bucket = "amrit-s3-backend-bucket-lf"
    force_destroy = true

    tags = {
      Name = "Amrit" ,
      Project = "Assignment"
    }
  
}

resource "aws_s3_bucket_versioning" "aws_s3_backend_bucket_versioning" {
    bucket = aws_s3_bucket.s3_backend_bucket.id
    versioning_configuration {
      status = "Enabled"
    }
  
}

## Enabling the encryption

resource "aws_s3_bucket_server_side_encryption_configuration" "backend_s3_encryption" {
    bucket = aws_s3_bucket.s3_backend_bucket.id
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }

  
}

resource "aws_s3_bucket_policy" "backend_bucket_policy" {
  bucket = aws_s3_bucket.s3_backend_bucket.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = { AWS = var.codebuild_iam_role_arn }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketVersioning",
          "s3:GetBucketAcl"
        ],
        Resource = [
          aws_s3_bucket.s3_backend_bucket.arn,
          "${aws_s3_bucket.s3_backend_bucket.arn}/*"
        ]
      } ,

      
    ]
  })
}


##TODO: Add the codebuild role arn here for backend bucket access 

# resource "aws_s3_bucket_policy" "s3_backend_bucket_policy" {
#   bucket = aws_s3_bucket.s3_backend_bucket.id
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#         {
#             Effect = "Allow" 
#               Principal = "*"
#             Action = [
#                   "s3:GetObject",
#           "s3:PutObject",
#           "s3:DeleteObject",
#           "s3:ListBucket"
#             ]
#             Resource = [
#           aws_s3_bucket.s3_backend_bucket.arn,
#           "${aws_s3_bucket.s3_backend_bucket.arn}/*"
#         ]
#         }
#     ]
#   })  
# }



## Bucket Policy Allowing only  the Lambda function to be able to access the bucekt 
## Change the Pricipal to the lambda ROLE ARN. 
## Get the Value from the main.tf that get the value from the lambda module. 

resource "aws_s3_bucket_policy" "s3_bucket_policy" {
  bucket = aws_s3_bucket.s3_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
        {
            Effect = "Allow"
            Principal = {
                AWS = [
                  var.data_ingestor_lambda_arn ,
                  var.data_analyzer_lambda_arn ,
                  var.notifier_lambda_arn

                ]
            }
            Action = [
                "s3:GetObject" ,
                "s3:PutObject"
            ]
            Resource = "${aws_s3_bucket.s3_bucket.arn}/*"
        } ,
        {
        Effect = "Allow",
        Principal = {
          AWS = var.codebuild_iam_role_arn
        },
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketVersioning",
          "s3:GetBucketAcl"
        ],
        Resource = [
          aws_s3_bucket.s3_bucket.arn,
          "${aws_s3_bucket.s3_bucket.arn}/*"
        ]
      }
    ]
  })  
}






### S3 Bucket Lifecycle Policy

resource "aws_s3_bucket_lifecycle_configuration" "s3_bucket_lifecycle" {
  bucket = aws_s3_bucket.s3_bucket.id
  rule {
    id     = "S3Bucket"
    status = "Enabled"



    filter {
      prefix = "" 
    }


    
    transition {
      days          = 30
      storage_class = "GLACIER" 
    }

    transition {
      days          = 180
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 365
    }
  }
}
