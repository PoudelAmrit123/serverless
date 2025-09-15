output "dynamoDb_arn" {
    value = aws_dynamodb_table.basic-dynamodb-table.arn
  
}

output "dynamoDb_table_name" {
    value = aws_dynamodb_table.basic-dynamodb-table.name
  
}