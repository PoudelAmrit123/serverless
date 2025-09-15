output "ses_primary" {
    value = aws_ses_email_identity.ses_email_primary.arn
  
}

output "ses_secondary" {
    value = aws_ses_email_identity.ses_email_secondary.arn
  
}