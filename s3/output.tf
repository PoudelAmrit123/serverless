output "bucket_arn" {
    value = aws_s3_bucket.s3_bucket.arn
  
}

# output "bucket_name" {
#     value = aws_s3_bucket.s3_bucket.bucket
  
# }

output "backend_bucket_arn" {
    value = aws_s3_bucket.s3_backend_bucket.arn
  
}

