
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
  name = "codebuild_iam_role_policy_s3_full"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # S3 bucket object-level permissions
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        Resource = [
          "${var.backend_bucket_arn}/*",
          "${var.s3_main_bucket_arn}/*",
          "${aws_s3_bucket.codepipeline_s3_bucket.arn}/*"
        ]
      },
      # S3 bucket-level permissions
      {
        Effect = "Allow",
        Action = [
          "s3:GetBucketPolicy",
          "s3:GetBucketAcl",
          "s3:GetBucketVersioning",
          "s3:GetBucketCors",
          "s3:ListBucket",
          "s3:GetBucketWebsite",
          "s3:GetAccelerateConfiguration",
          "s3:GetBucketRequestPayment",
          "s3:GetBucketReplication",
          "s3:GetBucketTagging",    
          "s3:GetBucketLogging",
          "s3:GetEncryptionConfiguration",
          "s3:GetLifecycleConfiguration",
          "s3:GetEncryptionConfiguration",
          "s3:GetReplicationConfiguration" ,
          "s3:GetBucketObjectLockConfiguration" ,
           "codepipeline:GetPipeline",
           "s3:GetBucketNotification",
            "codepipeline:GetPipelineState",
            "codepipeline:ListPipelines",
            "s3:GetBucketOwnershipControls" ,
            "s3:GetObjectVersion",
            "codepipeline:ListTagsForResource"
        ],
        Resource = [
          var.backend_bucket_arn,
          var.s3_main_bucket_arn,
          aws_s3_bucket.codepipeline_s3_bucket.arn,
          aws_codepipeline.codepipeline_project.arn
        ]
      },
      # CodeBuild project permissions
      {
        Effect = "Allow",
        Action = [
          "codebuild:BatchGetProjects",
          "codebuild:StartBuild"
        ],
        Resource = [
           aws_codebuild_project.codebuild_project.arn
        ] 
      },
      # Logging
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      },
     
            # TODO: Chnage the  dynamoDB to its own table arn
      {
        Effect = "Allow",
        Action = [
          "lambda:*",
          "dynamodb:*",
          
       
        ],
        Resource = "*"
      } ,

  #TODO: change the code connection  , ses , events to minimal like otheres 

      {
        Effect = "Allow",
        Action = [
        
           "codeconnections:GetConnection",
           "codeconnections:ListTagsForResource"
  # "codeconnections:ListConnections"
          
        ],
        Resource = aws_codestarconnections_connection.github.arn


      }, 
         {
        Effect = "Allow",
        Action = [
         "iam:GetRole",
    "iam:GetPolicy",
    "iam:ListRolePolicies",
    "iam:GetRolePolicy",
    "iam:ListAttachedRolePolicies",
    "iam:GetPolicyVersion",
      "iam:CreatePolicyVersion",
          
       
        ],
        Resource = "*"
      } ,
         {
        Effect = "Allow",
        Action = [
        
          "ses:SendEmail",
          "ses:SendRawEmail" , 
          "ses:VerifyEmailIdentity",
          "ses:GetIdentityVerificationAttributes",
        
          
        ],
        Resource = [
          var.ses_email_primary ,
          var.ses_email_secondary
        ]


      }, 
               {
        Effect = "Allow",
        Action = [
        
          "events:*",
          
        ],
        Resource = [
           var.notifier_rule,
           var.s3_processed_rule
        ]


      }, 


      {
  Effect = "Allow"
  Action = [
    "sns:CreateTopic",
    "sns:Subscribe",
    "sns:Publish",
    "sns:ListTopics" ,
      "sns:GetTopicAttributes",
      "sns:GetSubscriptionAttributes",
        "sns:ListTagsForResource",
    
   
  
  ]
  Resource = [
    var.sns_topic_arn ,
  
  ]
} ,
      {
  Effect = "Allow"
  Action = [
    
      "cloudwatch:ListTagsForResource",
        
           "cloudwatch:PutMetricAlarm",
    "cloudwatch:DescribeAlarms",
    "cloudwatch:DeleteAlarms",
    "cloudwatch:PutMetricData",
    "cloudwatch:GetMetricData",
  
  ]
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
    image                       = "aws/codebuild/standard:7.0"
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
          "s3:ListBucket" ,
           "s3:GetBucketPolicy" 
        ],
        Resource = [
          "${aws_s3_bucket.codepipeline_s3_bucket.arn}",
          "${aws_s3_bucket.codepipeline_s3_bucket.arn}/*",
           "arn:aws:s3:::amrit-s3-backend-bucket-lf/*",
           "arn:aws:s3:::amrit-s3-backend-bucket-lf" ,
            "arn:aws:s3:::amrit-s3-bucket-lf/*",
            
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



