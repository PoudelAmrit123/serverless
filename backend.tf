provider "aws" {

    region = "us-east-1"
  
}


terraform {
  backend "s3" {
    bucket = "amrit-s3-backend-bucket-lf"
    key = "terraform.tfstate"
    region = "us-east-1"
    use_lockfile = true
    
  }
}
