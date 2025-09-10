resource "aws_dynamodb_table" "basic-dynamodb-table" {
  name           = "BedrockResults"
  billing_mode   = "PAY_PER_REQUEST"
#   read_capacity  = 20
#   write_capacity = 20
  hash_key       = "correlation_id"
  range_key      = "Timestamp"

 attribute {
    name = "correlation_id"
    type = "S" 
  }


 attribute {
    name = "Timestamp"
    type = "S"  
  }

#   attribute {
#     name = "insights"
#     type = "S"
#   }

#   attribute {
#     name = "prompt"
#     type = "S"
#   }

#   ttl {
#     attribute_name = "TimeToExist"
#     enabled        = true
#   }

#   global_secondary_index {
#     name               = "GameTitleIndex"
#     hash_key           = "GameTitle"
#     range_key          = "TopScore"
#     write_capacity     = 10
#     read_capacity      = 10
#     projection_type    = "INCLUDE"
#     non_key_attributes = ["UserId"]
#   }

  tags = {
    Name        = "Amrit"
    Project = "serverless"
  }
}