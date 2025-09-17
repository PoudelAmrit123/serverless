import json
import boto3
import re
import html
from datetime import datetime, timezone
import logging

ses = boto3.client("ses")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("BedrockResults")

SOURCE_EMAIL = "amritpoudel433@gmail.com"
DEST_EMAIL = "officialamritpoudel433@gmail.com"
TOKEN_THRESHOLD = 50000 ## for testing threshold



logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log_json(level , message, correlation_id, **kwargs):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlationId": correlation_id,
        "message": message,
        "level": level ,
        **kwargs
    }
    print(json.dumps(log_entry))
    logger.log(level , json.dumps(log_entry))

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    # Extracting  correlation_id + timestamp
    correlation_id = event.get("detail", {}).get("correlation_id")
    timestamp = event.get("detail", {}).get("timestamp")

    log_json(logging.INFO, "Received event", correlation_id, event=event)
    if not correlation_id:
        log_json(logging.ERROR, "Missing correlation_id in event", None)
        return {"status": "failed", "reason": "missing correlation_id"}

    # Fetch record from DynamoDB 
    response = table.get_item(Key={
        "correlation_id": correlation_id,
        "Timestamp": timestamp
    })
    item = response.get("Item")
    if not item:
        log_json(logging.WARNING, "DynamoDB item not found", correlation_id)
        return {"status": "failed", "reason": "dynamodb item not found"}

    # Extract values
    result        = item.get("result", "")
    prompt        = item.get("prompt", "")
    input_tokens  = int(item.get("input_token", 0))
    output_tokens = int(item.get("output_token", 0))
    valid_rows    = int(item.get("valid_row", 0))
    invalid_rows  = int(item.get("invalid_row", 0))

    log_json(logging.INFO, "Fetched item from DynamoDB", correlation_id,
             input_tokens=input_tokens, output_tokens=output_tokens,
             valid_rows=valid_rows, invalid_rows=invalid_rows)

    # deetect anomalies 
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

    # extracting specific sections.
    def extract_section(section_name, text):
        pattern = rf"{section_name}\s*(.*?)(?=\n[A-Z ]+\n|$)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None

    overview       = extract_section("OVERVIEW OF BOOKS", result)
    highlights     = extract_section("COMPARATIVE HIGHLIGHTS", result)
    anomalies_text = extract_section("ANOMALIES", result)
    guidance       = extract_section("GUIDANCE FOR READERS", result)

    # ---- Modern Row/Token Counts Card ----
    html_counts = f"""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:16px; padding:24px; margin-bottom:24px; box-shadow: 0 8px 32px rgba(0,0,0,0.12); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #fff;'>
        <h2 style='margin: 0 0 16px 0;'>Processing Summary</h2>
        <div style='display:flex; flex-wrap:wrap; gap:12px;'>
            <div style='flex:1; min-width:120px; background: rgba(255,255,255,0.15); padding:16px; border-radius:12px; text-align:center;'>
                <div style='font-size:12px; text-transform: uppercase; opacity:0.8;'>Valid Rows</div>
                <div style='font-size:24px; font-weight:700;'>{valid_rows}</div>
            </div>
            <div style='flex:1; min-width:120px; background: rgba(255,255,255,0.15); padding:16px; border-radius:12px; text-align:center;'>
                <div style='font-size:12px; text-transform: uppercase; opacity:0.8;'>Invalid Rows</div>
                <div style='font-size:24px; font-weight:700;'>{invalid_rows}</div>
            </div>
            <div style='flex:1; min-width:120px; background: rgba(255,255,255,0.15); padding:16px; border-radius:12px; text-align:center;'>
                <div style='font-size:12px; text-transform: uppercase; opacity:0.8;'>Input Tokens</div>
                <div style='font-size:24px; font-weight:700;'>{input_tokens}</div>
            </div>
            <div style='flex:1; min-width:120px; background: rgba(255,255,255,0.15); padding:16px; border-radius:12px; text-align:center;'>
                <div style='font-size:12px; text-transform: uppercase; opacity:0.8;'>Output Tokens</div>
                <div style='font-size:24px; font-weight:700;'>{output_tokens}</div>
            </div>
        </div>
    </div>
    """

    # ---- Modern Sections Cards ----
    def section_card(title, content, color="#667eea"):
        if not content:
            content = "No information available."
        content_html = html.escape(content).replace("\n", "<br>")
        return f"""
        <div style='background:#fff; border-radius:16px; padding:28px; margin-bottom:24px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border:1px solid rgba(0,0,0,0.05); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;'>
            <h2 style='color:{color}; font-size:22px; font-weight:700; margin-bottom:16px;'>{title}</h2>
            <div style='color:#4B5563; font-size:15px; line-height:1.6; background:#F9FAFB; padding:16px; border-radius:12px; border-left:4px solid {color};'>
                {content_html}
            </div>
        </div>
        """

    html_overview   = section_card("Overview of Books", overview)
    html_highlights = section_card("Comparative Highlights", highlights, "#10B981")
    html_anomalies  = section_card("Anomalies", anomalies_text, "#EF4444")
    html_guidance   = section_card("Guidance for Readers", guidance, "#F59E0B")

    # ---- Responsive HTML Body ----
    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Book Processing Report</title></head>
    <body style="background:#f4f6f8; padding:20px; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color:#1F2937;">
        <div style="max-width:900px; margin:0 auto;">
            <h1 style='text-align:center; font-size:28px; font-weight:800; background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom:24px;'>Book Processing Report</h1>
            {html_counts}
            {html_overview}
            {html_highlights}
            {html_anomalies}
            {html_guidance}
        </div>
    </body>
    </html>
    """

    #  sending email
    try:
        ses.send_email(
            Source=SOURCE_EMAIL,
            Destination={"ToAddresses": [DEST_EMAIL]},
            Message={
                "Subject": {"Data": f"{'⚠️ Anomaly Detected' if anomalies else '✅ Processing Completed'} - Correlation ID {correlation_id}"},
                "Body": {"Html": {"Data": html_body}}
            }
        )
        log_json(logging.INFO, "SES email sent", correlation_id, destination=DEST_EMAIL)
    except Exception as e:
        log_json(logging.ERROR, "Failed to send SES email", correlation_id, error=str(e))
        raise


    return {
        "status": "success",
        "correlation_id": correlation_id,
        "notified_to": DEST_EMAIL,
        "anomalies_found": anomalies
    }














# import json
# import boto3
# import re

# ses = boto3.client("ses")
# dynamodb = boto3.resource("dynamodb")
# table = dynamodb.Table("BedrockResults")

# SOURCE_EMAIL = "amritpoudel433@gmail.com"
# DEST_EMAIL   = "officialamritpoudel433@gmail.com"
# TOKEN_THRESHOLD = 50000

# def lambda_handler(event, context):
#     print("Received event:", json.dumps(event))

#     # Extract correlation_id + timestamp
#     correlation_id = event.get("detail", {}).get("correlation_id")
#     timestamp = event.get("detail", {}).get("timestamp")
#     if not correlation_id:
#         return {"status": "failed", "reason": "missing correlation_id"}

#     # Fetch record from DynamoDB
#     response = table.get_item(Key={
#         "correlation_id": correlation_id,
#         "Timestamp": timestamp
#     })
#     item = response.get("Item")
#     if not item:
#         return {"status": "failed", "reason": "dynamodb item not found"}

#     # Extract values
#     result        = item.get("result", "")
#     prompt        = item.get("prompt", "")
#     input_tokens  = int(item.get("input_token", 0))
#     output_tokens = int(item.get("output_token", 0))
#     valid_rows    = int(item.get("valid_row", 0))
#     invalid_rows  = int(item.get("invalid_row", 0))

#     # ---- Detect anomalies ----
#     anomalies = []
#     bad_phrases = [
#         "no answer",
#         "null",
#         "not available",
#         "i'm sorry, but i can't provide specific details",
#         "cannot provide specific details",
#         "can't provide specific"
#     ]
#     if not result or any(phrase in result.lower() for phrase in bad_phrases):
#         anomalies.append("LLM did not return a valid answer.")
#     if (input_tokens + output_tokens) > TOKEN_THRESHOLD:
#         anomalies.append("Token usage exceeded safe threshold.")
#     if valid_rows < invalid_rows:
#         anomalies.append("Invalid rows exceed valid rows.")

#     # ---- Parse sections from result ----
#     def extract_section(section_name, text):
#         pattern = rf"{section_name}\s*(.*?)(?=\n[A-Z ]+\n|$)"
#         match = re.search(pattern, text, re.DOTALL)
#         return match.group(1).strip() if match else None

#     overview       = extract_section("OVERVIEW OF BOOKS", result)
#     highlights     = extract_section("COMPARATIVE HIGHLIGHTS", result)
#     anomalies_text = extract_section("ANOMALIES", result)
#     guidance       = extract_section("GUIDANCE FOR READERS", result)

#     # ---- Build modern HTML email ----
#     body_html = f"""
#     <html>
#       <head>
#         <style>
#           body {{
#               font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
#               background-color: #f4f6f8;
#               color: #333;
#               margin: 0; padding: 0;
#           }}
#           .container {{
#               max-width: 700px;
#               margin: 20px auto;
#               background: #ffffff;
#               border-radius: 10px;
#               box-shadow: 0 4px 15px rgba(0,0,0,0.1);
#               padding: 25px;
#           }}
#           h2 {{
#               font-size: 22px;
#               margin-bottom: 10px;
#           }}
#           h2.success {{ color: #28a745; }}
#           h2.anomaly {{ color: #dc3545; }}
#           h3 {{
#               font-size: 18px;
#               margin-bottom: 6px;
#               color: #007bff;
#           }}
#           .section {{
#               margin-bottom: 20px;
#           }}
#           pre {{
#               background: #f1f3f5;
#               padding: 12px;
#               border-radius: 6px;
#               overflow-x: auto;
#               white-space: pre-wrap;
#               word-wrap: break-word;
#           }}
#           ul {{
#               padding-left: 20px;
#           }}
#           li {{
#               margin-bottom: 6px;
#           }}
#           p {{
#               margin: 5px 0;
#           }}
#         </style>
#       </head>
#       <body>
#         <div class="container">
#           <h2 class="{'anomaly' if anomalies else 'success'}">
#               {'⚠️ Anomaly Detected' if anomalies else '✅ Processing Completed Successfully'}
#           </h2>

#           <div class="section">
#               <p><b>Correlation ID:</b> {correlation_id}</p>
#               <p>Tokens → Input: {input_tokens}, Output: {output_tokens}</p>
#               <p>Rows → Valid: {valid_rows}, Invalid: {invalid_rows}</p>
#           </div>
#     """

#     if anomalies:
#         body_html += f"""
#         <div class="section">
#             <p><b>Issues Detected:</b></p>
#             <ul>
#                 {''.join([f'<li>{a}</li>' for a in anomalies])}
#             </ul>
#         </div>
#         """

#     if overview:
#         body_html += f"""
#         <div class="section">
#             <h3>Overview of Books</h3>
#             <pre>{overview}</pre>
#         </div>
#         """
#     if highlights:
#         body_html += f"""
#         <div class="section">
#             <h3>Comparative Highlights</h3>
#             <pre>{highlights}</pre>
#         </div>
#         """
#     if anomalies_text:
#         body_html += f"""
#         <div class="section">
#             <h3>Anomalies</h3>
#             <pre>{anomalies_text}</pre>
#         </div>
#         """
#     if guidance:
#         body_html += f"""
#         <div class="section">
#             <h3>Guidance for Readers</h3>
#             <pre>{guidance}</pre>
#         </div>
#         """

#     body_html += "</div></body></html>"

#     # ---- Send email ----
#     ses.send_email(
#         Source=SOURCE_EMAIL,
#         Destination={"ToAddresses": [DEST_EMAIL]},
#         Message={
#             "Subject": {"Data": f"{'⚠️ Anomaly Detected' if anomalies else '✅ Processing Completed'} - Correlation ID {correlation_id}"},
#             "Body": {"Html": {"Data": body_html}}
#         }
#     )

#     return {
#         "status": "success",
#         "correlation_id": correlation_id,
#         "notified_to": DEST_EMAIL,
#         "anomalies_found": anomalies
#     }



