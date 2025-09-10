        
        
        
        resource "aws_cloudwatch_event_rule" "s3_processed_rule" {
        name        = "s3_processed_data_rule"
        description = "Trigger Bedrock Lambda when processed data is uploaded"
        event_pattern = jsonencode({
            "source": ["aws.s3"],
            "detail-type": ["Object Created"],
            "detail": {
            "bucket": {
                "name": ["amrit-s3-bucket-lf"]
            },
            "object": {
                "key": [{"prefix": "processed/selected_data.json"}]
            }
            }
        })
        }

        resource "aws_cloudwatch_event_target" "bedrock_lambda_target" {
        rule      = aws_cloudwatch_event_rule.s3_processed_rule.name
        target_id = "BedrockLambda"
        arn       = var.lambda_function_arn
        }

        resource "aws_lambda_permission" "allow_eventbridge" {
        statement_id  = "AllowExecutionFromEventBridge"
        action        = "lambda:InvokeFunction"
        function_name = var.lambda_function_name
        principal     = "events.amazonaws.com"
        source_arn    = aws_cloudwatch_event_rule.s3_processed_rule.arn
        }
