resource "aws_ses_email_identity" "ses_email_primary" {
  email = "amritpoudel433@gmail.com"
}

resource "aws_ses_email_identity" "ses_email_secondary" {
  email = "officialamritpoudel433@gmail.com"
}