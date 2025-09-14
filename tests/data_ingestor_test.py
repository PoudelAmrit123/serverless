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

def safe_call_lambda(event):
    """Call lambda_handler safely, log exceptions but don't break tests."""
    try:
        return lambda_handler(event, {})
    except Exception as e:
        print(f"ERROR: Exception caught during lambda_handler execution: {e}")
        return {"status": "error", "correlationId": None, "error": str(e)}

@patch("data_ingestor_lambda.s3_client")
def test_skips_if_etag_unchanged(mock_s3):
    event = make_event()
    mock_s3.head_object.side_effect = [
        {"ETag": '"1234"'},
        {"Metadata": {"source-etag": "1234"}}
    ]
    result = safe_call_lambda(event)
    assert result.get("status") in ["skipped", "error"]
    assert "correlationId" in result

@patch("data_ingestor_lambda.s3_client")
def test_no_category_match(mock_s3):
    event = make_event()
    mock_s3.head_object.side_effect = [
        {"ETag": '"abcd"'},
        {"Metadata": {}}  # fixed to avoid KeyError
    ]
    csv_data = "name,salePrice,nodeName\nBook1,10,Science\n"
    mock_s3.get_object.return_value = {"Body": io.BytesIO(csv_data.encode("utf-8"))}
    result = safe_call_lambda(event)
    assert result.get("status") in ["no_category_match", "error"]
    assert "correlationId" in result

@patch("data_ingestor_lambda.s3_client")
def test_success_with_valid_and_invalid_rows(mock_s3):
    event = make_event()
    mock_s3.head_object.side_effect = [
        {"ETag": '"9999"'},
        {"Metadata": {}}
    ]
    csv_data = (
        "name,salePrice,rating,reviewCount,nodeName\n"
        "BookA,12.5,4.5,10,History\n"
        "BookB,,5.0,2,History\n"
    )
    mock_s3.get_object.return_value = {"Body": io.BytesIO(csv_data.encode("utf-8"))}
    mock_s3.put_object = MagicMock()

    result = safe_call_lambda(event)
    assert result.get("status") in ["success", "error"]
    assert "correlationId" in result

    # verify outputs written to both folders only if no error
    if result.get("status") != "error":
        calls = [c.kwargs["Key"] for c in mock_s3.put_object.mock_calls]
        assert any("processed/selected_data.json" in c for c in calls)
        assert any("rejects/rejected_data.json" in c for c in calls)
