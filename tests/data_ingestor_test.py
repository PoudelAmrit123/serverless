import io
import pytest
from unittest.mock import patch, MagicMock
import sys, os

# Make sure Python can find the Lambda file
sys.path.append(os.path.join(os.path.dirname(__file__), "../lambda/boto3"))

from data_ingestor_lambda import lambda_handler  # your Lambda function

def make_event(bucket="test-bucket", key="input.csv"):
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

@patch("data_ingestor_lambda.s3_client")
def test_skips_if_etag_unchanged(mock_s3):
    event = make_event()
    mock_s3.head_object.side_effect = [
        {"ETag": '"1234"'},
        {"Metadata": {"source-etag": "1234"}}
    ]
    result = lambda_handler(event, {})
    assert result["status"] == "skipped"
    assert "correlationId" in result

@patch("data_ingestor_lambda.s3_client")
def test_no_category_match(mock_s3):
    event = make_event()
    mock_s3.head_object.side_effect = [
        {"ETag": '"abcd"'},
        {}
    ]
    csv_data = "name,salePrice,nodeName\nBook1,10,Science\n"
    mock_s3.get_object.return_value = {"Body": io.BytesIO(csv_data.encode("utf-8"))}
    result = lambda_handler(event, {})
    assert result["status"] == "no_category_match"
    assert "correlationId" in result

@patch("data_ingestor_lambda.s3_client")
def test_success_with_valid_and_invalid_rows(mock_s3):
    event = make_event()
    mock_s3.head_object.side_effect = [
        {"ETag": '"9999"'},
        {"Metadata": {"source-etag": "old"}}
    ]
    csv_data = (
        "name,salePrice,rating,reviewCount,nodeName\n"
        "BookA,12.5,4.5,10,History\n"
        "BookB,,5.0,2,History\n"
    )
    mock_s3.get_object.return_value = {"Body": io.BytesIO(csv_data.encode("utf-8"))}
    mock_s3.put_object = MagicMock()

    result = lambda_handler(event, {})
    assert result["status"] == "success"
    assert "correlationId" in result

    calls = [c.kwargs["Key"] for c in mock_s3.put_object.mock_calls]
    assert any("processed/selected_data.json" in c for c in calls)
    assert any("rejects/rejected_data.json" in c for c in calls)
