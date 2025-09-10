output "lambda_role_arn" {
    value = aws_iam_role.lambda_iam_role.arn
  
}

output "data_analyzer_function_arn" {

    value = aws_lambda_function.data_analyzer_function.arn

  
}

output "data_analyzer_function_function_name" {
 value = aws_lambda_function.data_analyzer_function.function_name
  
}

output "notifier_lambda_arn" {
    value = aws_lambda_function.notifier_function.arn
  
}

output "notifier_lambda_name" {
    value = aws_lambda_function.notifier_function.function_name
  
}