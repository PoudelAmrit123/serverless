resource "aws_s3_bucket" "s3_bucket" {

    bucket = "amrit-s3-bucket-lf"

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
                AWS = ""
            }
            Action = [
                "s3:GetObject" ,
                "s3:PutObject"
            ]
            Resource = "${aws_s3_bucket.s3_bucket.arn}/*"
        }
    ]
  })  
}


### IAM Role Later Move it to Seperate Module 
