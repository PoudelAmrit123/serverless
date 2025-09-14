variable "lambda_names" {
    description = "name of the lambda function"
  type = set(string)

  default = [ "data_ingestor_function" , "data_analyzer_function" , "notifier_function" ]
  
}