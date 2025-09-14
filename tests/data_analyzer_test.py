import io
import json
import pytest
from unittest.mock import patch, MagicMock
import sys, os

# Ensure Python can find your Lambda file
sys.path.append(os.path.join(os.path.dirname(__file__), "../lambda/boto3"))

from data_ingestor_lambda import lambda_handler

# ----------- Helper to create fake S3 events -----------------
def make_event(bucket="test-bucket", key="processed/selected_data.json"):
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": key}
                }
            }
        ]
    }

# ----------- Test: skipped file (wrong key) -----------------
@patch("data_ingestor_lambda.s3_client")
def test_skips_if_not_target_file(mock_s3):
    event = make_event(key="raw/some_other_file.json")
    result = lambda_handler(event, {})
    assert result["status"] == "skipped"
    assert "correlation_id" in result

# ----------- Test: normal processing flow -------------------
@patch("data_ingestor_lambda.eventbridge")
@patch("data_ingestor_lambda.table")
@patch("data_ingestor_lambda.bedrock")
@patch("data_ingestor_lambda.s3_client")
def test_success_processing(mock_s3, mock_bedrock, mock_table, mock_eventbridge):
    event = make_event()

    # Mock S3 get_object response
    sample_data = [
        {"name": "Book1", "salePrice": 4.5, "rating": 4.6, "description": "desc1"},
        {"name": "Book2", "salePrice": 6.0, "rating": 4.2, "description": "desc2"},
    ]
    mock_s3.get_object.return_value = {
        "Body": io.BytesIO(json.dumps(sample_data).encode("utf-8")),
        "Metadata": {
            "correlation_id": "1234",
            "valid_count": "1",
            "invalid_count": "1"
        }
    }

    # Mock Bedrock response
    bedrock_response = {
        "body": io.BytesIO(json.dumps({
            "output_text": {"output": {"message": {"content": [{"text": "Best Book is Book1"}]}}},
            "usage": {"inputTokens": 10, "outputTokens": 5}
        }).encode("utf-8"))
    }
    mock_bedrock.invoke_model.return_value = bedrock_response

    # Mock DynamoDB put_item and EventBridge put_events
    mock_table.put_item = MagicMock()
    mock_eventbridge.put_events = MagicMock()
    mock_s3.put_object = MagicMock()

    result = lambda_handler(event, {})

    assert result["status"] == "success"
    assert "correlation_id" in result
    assert result["s3_output"] == "processed/bedrock_response.json"

    # Check S3 put_object called
    calls = [c.kwargs["Key"] for c in mock_s3.put_object.mock_calls]
    assert "processed/bedrock_response.json" in calls

    # Check DynamoDB put_item called once
    assert mock_table.put_item.call_count == 1

    # Check EventBridge called once
    assert mock_eventbridge.put_events.call_count == 1

# ----------- Test: extract_summary and extract_usage fail gracefully -----
def test_extract_summary_usage_error_handling():
    from data_ingestor_lambda import extract_summary, extract_usage
    bad_data = {"output": {"message": {"content": None}}}

    assert extract_summary(bad_data) is None
    assert extract_usage({}) == {"input_tokens": None, "output_tokens": None}
