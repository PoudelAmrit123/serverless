import json
import boto3

ses = boto3.client("ses")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("BedrockResults")
bedrock = boto3.client("bedrock-runtime")  # AWS Bedrock client

SOURCE_EMAIL = "amritpoudel433@gmail.com"
DEST_EMAIL   = "officialamritpoudel433@gmail.com"

TOKEN_THRESHOLD = 50000

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    # Extract correlation_id + timestamp
    correlation_id = event.get("detail", {}).get("correlation_id")
    timestamp = event.get("detail", {}).get("timestamp")
    if not correlation_id:
        return {"status": "failed", "reason": "missing correlation_id"}

    # Fetch record from DynamoDB
    response = table.get_item(Key={
        "correlation_id": correlation_id,
        "Timestamp": timestamp
    })
    item = response.get("Item")
    if not item:
        return {"status": "failed", "reason": "dynamodb item not found"}

    # Extract values
    result       = item.get("result", "")
    prompt       = item.get("prompt", "")
    input_tokens = int(item.get("input_token", 0))
    output_tokens= int(item.get("output_token", 0))
    valid_rows   = int(item.get("valid_row", 0))
    invalid_rows = int(item.get("invalid_row", 0))

    # ---- Detect anomalies ----
    anomalies = []
    bad_phrases = [
        "no answer",
        "null",
        "not available",
        "i'm sorry, but i can't provide specific details",
        "cannot provide specific details",
        "can't provide specific"
    ]
    if not result or any(phrase in result.lower() for phrase in bad_phrases):
        anomalies.append("LLM did not return a valid answer.")
    if (input_tokens + output_tokens) > TOKEN_THRESHOLD:
        anomalies.append("Token usage exceeded safe threshold.")
    if valid_rows < invalid_rows:
        anomalies.append("Invalid rows exceed valid rows.")

    # ---- Call Bedrock for executive summary (always) ----

    prompt = """
Provide an executive summary for the following processed data. 
Include correlation ID, original prompt, result, token usage, and row counts.
"""

# Construct text to pass to Bedrock
    prompt_with_data = f"""{prompt}

      Correlation ID: {correlation_id}
      Prompt: {prompt}
      Result: {result}
      Tokens → Input: {input_tokens}, Output: {output_tokens}
      Rows → Valid: {valid_rows}, Invalid: {invalid_rows}
      """
    
    # summary = ""
    # try:
    #     bedrock_response = bedrock.invoke_model(
    #         modelId="amazon.nova-micro-v1:0",  # replace with your Bedrock model
    #         body=json.dumps({
    #         "messages": [
    #             {
    #                 "role": "user",
    #                 "content": [{"text": prompt_with_data}]
    #             }
    #         ]
    #           }),
    #         contentType="application/json",
    #         accept="application/json"
    #     )
    #     summary_response = json.loads(bedrock_response["body"].read())
    #     summary = summary_response.get("summary", "")
    # except Exception as e:
    #     print("Bedrock summary call failed:", str(e))
    #     summary = "Summary unavailable due to Bedrock error."

    # ---- Build email ----
    if anomalies:
        subject = f"⚠️ Anomaly Detected - Correlation ID {correlation_id}"
        body_html = f"""
        <html>
          <head>
            <style>
              body {{ font-family: Arial, sans-serif; }}
              .anomaly {{ color: red; font-weight: bold; }}
              .section {{ margin-bottom: 12px; }}
            </style>
          </head>
          <body>
            <h2 class="anomaly">Anomaly Detected in Processing</h2>
            <p><b>Correlation ID:</b> {correlation_id}</p>

            <div class="section">
              <p><b>Issues:</b></p>
              <ul>
                {''.join([f"<li>{a}</li>" for a in anomalies])}
              </ul>
            </div>

            <div class="section">
              <p><b>Executive Summary:</b> {summary}</p>
            </div>

            <div class="section">
              <p><b>Full Result:</b> {result}</p>
              <p>Tokens → Input: {input_tokens}, Output: {output_tokens}</p>
              <p>Rows → Valid: {valid_rows}, Invalid: {invalid_rows}</p>
            </div>
          </body>
        </html>
        """
    else:
        subject = f"✅ Processing Completed - Correlation ID {correlation_id}"
        body_html = f"""
        <html>
          <head>
            <style>
              body {{ font-family: Arial, sans-serif; }}
              .success {{ color: green; font-weight: bold; }}
              .section {{ margin-bottom: 12px; }}
            </style>
          </head>
          <body>
            <h2 class="success">Processing Completed Successfully</h2>
            <p><b>Correlation ID:</b> {correlation_id}</p>

            <div class="section">
              <p><b>Executive Summary:</b> {summary}</p>
            </div>

            <div class="section">
              <p><b>Full Result:</b> {result}</p>
              <p>Tokens → Input: {input_tokens}, Output: {output_tokens}</p>
              <p>Rows → Valid: {valid_rows}, Invalid: {invalid_rows}</p>
            </div>
          </body>
        </html>
        """

    # ---- Send email ----
    ses.send_email(
        Source=SOURCE_EMAIL,
        Destination={"ToAddresses": [DEST_EMAIL]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Html": {"Data": body_html}}
        }
    )

    return {
        "status": "success",
        "correlation_id": correlation_id,
        "notified_to": DEST_EMAIL,
        "anomalies_found": anomalies,
        "executive_summary": summary
    }
