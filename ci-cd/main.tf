
### Code build 


resource "aws_s3_bucket" "codepipeline_s3_bucket" {
  bucket = "amrit-code-build-lf"
  force_destroy = true 

   tags = {
      Name = "Amrit" ,
      Project = "Assignment"
    }
}



resource "aws_s3_bucket_versioning" "codepipeline_s3_bucket_versioning" {
    bucket = aws_s3_bucket.codepipeline_s3_bucket.id
    versioning_configuration {
      status = "Enabled"
    }
  
}

# resource "aws_s3_bucket_acl" "example" {
#   bucket = aws_s3_bucket.example.id
#   acl    = "private"
# }

resource "aws_iam_role" "codebuild_iam_role" {
    name = "amrit-codebuld-role"

      assume_role_policy = jsonencode({
  Version: "2012-10-17",
  Statement: [
    {
      Effect: "Allow",
      Action: "sts:AssumeRole",
     Principal = {
          Service = [
            "codebuild.amazonaws.com",
            "codepipeline.amazonaws.com"
          ]
        }
    
    }
  ]
}) 
  
}

resource "aws_iam_policy" "codebuild_iam_policy" {
  name = "codebuild_iam_role_policy_s3"
  policy = jsonencode({
    Version: "2012-10-17",
    Statement: [
      {
        Effect = "Allow",
        Action = [
         "s3:GetObject",
  "s3:PutObject",
  "s3:DeleteObject",
  "s3:ListBucket",
  "s3:GetBucketVersioning",
  "s3:GetBucketAcl"

        ],
        Resource = [
          "${aws_s3_bucket.codepipeline_s3_bucket.arn}/*" ,
          "arn:aws:s3:::amrit-s3-backend-bucket-lf/*" ,
           "arn:aws:s3:::amrit-s3-backend-bucket-lf"
           
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "s3:ListBucket" ,
           "s3:GetBucketVersioning",
    "s3:GetBucketAcl"
        ],
        Resource = [
          "${aws_s3_bucket.codepipeline_s3_bucket.arn}" ,
          
        ]
      } ,
      {
  Effect = "Allow",
  Action = [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  Resource = "*"
}
    
   

    ]
  })
}


resource "aws_iam_role_policy_attachment" "codebuild_iam_role_policy_attachment" {
    policy_arn = aws_iam_policy.codebuild_iam_policy.arn
    role = aws_iam_role.codebuild_iam_role.name
  

}


resource "aws_codebuild_project" "codebuild_project" {
  name          = "amrit-codebuild"
  service_role  = aws_iam_role.codebuild_iam_role.arn
  artifacts {
    type = "CODEPIPELINE"
  }
  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux2-x86_64-standard:4.0"
    type                        = "LINUX_CONTAINER"
    privileged_mode             = false
  }
  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec.yml"  
  }
}


#### Code Pipeline 


### Github Connection

resource "aws_codestarconnections_connection" "github" {
    provider_type = "GitHub"
    name = "github-connection"
  
}


# IAM Role for CodePipeline
resource "aws_iam_role" "codepipeline_role" {
  name = "amrit-codepipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "codepipeline.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}


# IAM Policy for CodePipeline (separate resource)
resource "aws_iam_policy" "codepipeline_policy" {
  name = "codepipeline_iam_role_policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # Allow CodePipeline to access S3 artifact bucket
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetBucketVersioning",
          "s3:ListBucket"
        ],
        Resource = [
          "${aws_s3_bucket.codepipeline_s3_bucket.arn}",
          "${aws_s3_bucket.codepipeline_s3_bucket.arn}/*",
           "arn:aws:s3:::amrit-s3-backend-bucket-lf/*",
           "arn:aws:s3:::amrit-s3-backend-bucket-lf"
        ]
      },
      # Allow CodePipeline to trigger CodeBuild
      {
        Effect = "Allow",
        Action = [
          "codebuild:BatchGetBuilds",
          "codebuild:StartBuild"
        ],
        Resource = [
          aws_codebuild_project.codebuild_project.arn
        ]
      },
      # Allow use of CodeStar connection (GitHub)
      {
        Effect = "Allow",
        Action = [
          "codestar-connections:UseConnection"
        ],
        Resource = aws_codestarconnections_connection.github.arn
      },
      # Allow logging
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach the custom policy to CodePipeline IAM Role
resource "aws_iam_role_policy_attachment" "codepipeline_role_policy_attachment" {
  policy_arn = aws_iam_policy.codepipeline_policy.arn
  role       = aws_iam_role.codepipeline_role.name
}



resource "aws_codepipeline" "codepipeline_project" {
    name =   "amrit-codepipeline"
    artifact_store {
        location = aws_s3_bucket.codepipeline_s3_bucket.bucket
        type = "S3"
       
    }

    role_arn = aws_iam_role.codepipeline_role.arn

    stage {
      name = "Source"
      action {
        name = "Source"
        category = "Source"
          configuration = {
        ConnectionArn    = aws_codestarconnections_connection.github.arn
        FullRepositoryId = "PoudelAmrit123/serverless"
        BranchName       = "main"
      }
        owner = "AWS"
        version = 1
        provider = "CodeStarSourceConnection"
        output_artifacts = [ "source_output" ]
      }
    }

        stage {
      name = "Build"
      action {
        name = "Build"
        category = "Build"
            configuration = {
               ProjectName = aws_codebuild_project.codebuild_project.name
      }
        owner = "AWS"
        version = 1
        provider = "CodeBuild"
        input_artifacts  = ["source_output"]   
        output_artifacts = [ "build_output" ]
      }
    }

  
}



