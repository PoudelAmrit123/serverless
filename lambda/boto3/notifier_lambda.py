import json
import boto3
import re

ses = boto3.client("ses")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("BedrockResults")

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
    result        = item.get("result", "")
    prompt        = item.get("prompt", "")
    input_tokens  = int(item.get("input_token", 0))
    output_tokens = int(item.get("output_token", 0))
    valid_rows    = int(item.get("valid_row", 0))
    invalid_rows  = int(item.get("invalid_row", 0))

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

    # ---- Parse sections from result ----
    def extract_section(section_name, text):
        pattern = rf"{section_name}\s*(.*?)(?=\n[A-Z ]+\n|$)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None

    overview       = extract_section("OVERVIEW OF BOOKS", result)
    highlights     = extract_section("COMPARATIVE HIGHLIGHTS", result)
    anomalies_text = extract_section("ANOMALIES", result)
    guidance       = extract_section("GUIDANCE FOR READERS", result)

    # ---- Build modern HTML email ----
    body_html = f"""
    <html>
      <head>
        <style>
          body {{
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
              background-color: #f4f6f8;
              color: #333;
              margin: 0; padding: 0;
          }}
          .container {{
              max-width: 700px;
              margin: 20px auto;
              background: #ffffff;
              border-radius: 10px;
              box-shadow: 0 4px 15px rgba(0,0,0,0.1);
              padding: 25px;
          }}
          h2 {{
              font-size: 22px;
              margin-bottom: 10px;
          }}
          h2.success {{ color: #28a745; }}
          h2.anomaly {{ color: #dc3545; }}
          h3 {{
              font-size: 18px;
              margin-bottom: 6px;
              color: #007bff;
          }}
          .section {{
              margin-bottom: 20px;
          }}
          pre {{
              background: #f1f3f5;
              padding: 12px;
              border-radius: 6px;
              overflow-x: auto;
              white-space: pre-wrap;
              word-wrap: break-word;
          }}
          ul {{
              padding-left: 20px;
          }}
          li {{
              margin-bottom: 6px;
          }}
          p {{
              margin: 5px 0;
          }}
        </style>
      </head>
      <body>
        <div class="container">
          <h2 class="{'anomaly' if anomalies else 'success'}">
              {'⚠️ Anomaly Detected' if anomalies else '✅ Processing Completed Successfully'}
          </h2>

          <div class="section">
              <p><b>Correlation ID:</b> {correlation_id}</p>
              <p>Tokens → Input: {input_tokens}, Output: {output_tokens}</p>
              <p>Rows → Valid: {valid_rows}, Invalid: {invalid_rows}</p>
          </div>
    """

    if anomalies:
        body_html += f"""
        <div class="section">
            <p><b>Issues Detected:</b></p>
            <ul>
                {''.join([f'<li>{a}</li>' for a in anomalies])}
            </ul>
        </div>
        """

    if overview:
        body_html += f"""
        <div class="section">
            <h3>Overview of Books</h3>
            <pre>{overview}</pre>
        </div>
        """
    if highlights:
        body_html += f"""
        <div class="section">
            <h3>Comparative Highlights</h3>
            <pre>{highlights}</pre>
        </div>
        """
    if anomalies_text:
        body_html += f"""
        <div class="section">
            <h3>Anomalies</h3>
            <pre>{anomalies_text}</pre>
        </div>
        """
    if guidance:
        body_html += f"""
        <div class="section">
            <h3>Guidance for Readers</h3>
            <pre>{guidance}</pre>
        </div>
        """

    body_html += "</div></body></html>"

    # ---- Send email ----
    ses.send_email(
        Source=SOURCE_EMAIL,
        Destination={"ToAddresses": [DEST_EMAIL]},
        Message={
            "Subject": {"Data": f"{'⚠️ Anomaly Detected' if anomalies else '✅ Processing Completed'} - Correlation ID {correlation_id}"},
            "Body": {"Html": {"Data": body_html}}
        }
    )

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

#     # ---- Build HTML email ----
#     body_html = f"""
#     <html>
#       <head>
#         <style>
#           body {{ font-family: Arial, sans-serif; }}
#           .section {{ margin-bottom: 16px; }}
#           .anomaly {{ color: red; font-weight: bold; }}
#           .success {{ color: green; font-weight: bold; }}
#           h2 {{ margin-bottom: 8px; }}
#         </style>
#       </head>
#       <body>
#         <h2 class="{'anomaly' if anomalies else 'success'}">
#             {'⚠️ Anomaly Detected' if anomalies else '✅ Processing Completed Successfully'}
#         </h2>

#         <div class="section">
#             <p><b>Correlation ID:</b> {correlation_id}</p>
#             <p>Tokens → Input: {input_tokens}, Output: {output_tokens}</p>
#             <p>Rows → Valid: {valid_rows}, Invalid: {invalid_rows}</p>
#         </div>
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

#     # Add parsed sections
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

#     body_html += "</body></html>"

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































# import json
# import boto3
# import re

# ses = boto3.client("ses")
# dynamodb = boto3.resource("dynamodb")
# table = dynamodb.Table("BedrockResults")

# SOURCE_EMAIL = "amritpoudel433@gmail.com"
# DEST_EMAIL = "officialamritpoudel433@gmail.com"
# TOKEN_THRESHOLD = 50000

# SECTION_HEADERS = [
#     "OVERVIEW OF BOOKS",
#     "COMPARATIVE HIGHLIGHTS",
#     "ANOMALIES",
#     "GUIDANCE FOR READERS"
# ]

# def lambda_handler(event, context):
#     # Extract correlation_id + timestamp from EventBridge event
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
#     result = item.get("result", "")
#     input_tokens = int(item.get("input_token", 0))
#     output_tokens = int(item.get("output_token", 0))
#     valid_rows = int(item.get("valid_row", 0))
#     invalid_rows = int(item.get("invalid_row", 0))

#     # ---- Detect anomalies ----
#     anomalies_detected = []
#     bad_phrases = [
#         "no answer",
#         "null",
#         "not available",
#         "i'm sorry, but i can't provide specific details",
#         "cannot provide specific details",
#         "can't provide specific"
#     ]
#     if not result or any(phrase in result.lower() for phrase in bad_phrases):
#         anomalies_detected.append("LLM did not return a valid answer.")
#     if (input_tokens + output_tokens) > TOKEN_THRESHOLD:
#         anomalies_detected.append("Token usage exceeded safe threshold.")
#     if valid_rows < invalid_rows:
#         anomalies_detected.append("Invalid rows exceed valid rows.")

#     # ---- Parse sections from result ----
#     sections = {}
#     for i, header in enumerate(SECTION_HEADERS):
#         pattern = rf"{header}\s*(.*?)(?=(?:{'|'.join(SECTION_HEADERS[i+1:])})|$)"
#         match = re.search(pattern, result, flags=re.DOTALL | re.IGNORECASE)
#         if match:
#             sections[header] = match.group(1).strip()
#         else:
#             sections[header] = ""

#     # ---- Build HTML email ----
#     subject = f"✅ Processing Completed - Correlation ID {correlation_id}" if not anomalies_detected else f"⚠️ Anomaly Detected - Correlation ID {correlation_id}"

#     body_html = f"""
#     <html>
#       <head>
#         <style>
#           body {{ font-family: Arial, sans-serif; line-height: 1.5; }}
#           h2 {{ color: {'red' if anomalies_detected else 'green'}; }}
#           .section {{ margin-bottom: 15px; }}
#           .book {{ margin-bottom: 10px; padding-left: 15px; }}
#           ul {{ margin-top: 0; }}
#         </style>
#       </head>
#       <body>
#         <h2>{'Anomaly Detected' if anomalies_detected else 'Processing Completed Successfully'}</h2>
#         <p><b>Correlation ID:</b> {correlation_id}</p>

#         <div class="section">
#           <h3>Metadata</h3>
#           <ul>
#             <li>Input Tokens: {input_tokens}</li>
#             <li>Output Tokens: {output_tokens}</li>
#             <li>Valid Rows: {valid_rows}</li>
#             <li>Invalid Rows: {invalid_rows}</li>
#           </ul>
#         </div>

#         {"<div class='section'><h3>Anomalies Detected</h3><ul>" + "".join([f"<li>{a}</li>" for a in anomalies_detected]) + "</ul></div>" if anomalies_detected else ""}

#         {generate_section_html(sections)}
#       </body>
#     </html>
#     """

#     # ---- Send email via SES ----
#     ses.send_email(
#         Source=SOURCE_EMAIL,
#         Destination={"ToAddresses": [DEST_EMAIL]},
#         Message={
#             "Subject": {"Data": subject},
#             "Body": {"Html": {"Data": body_html}}
#         }
#     )

#     return {
#         "status": "success",
#         "correlation_id": correlation_id,
#         "notified_to": DEST_EMAIL,
#         "anomalies_found": anomalies_detected
#     }


# def generate_section_html(sections):
#     """Convert parsed sections into HTML blocks."""
#     html_blocks = []

#     # Overview: each book in <div class="book">
#     overview = sections.get("OVERVIEW OF BOOKS", "")
#     books = re.split(r'"\s*(.*?)"\s+provides', overview)
#     if len(books) > 1:
#         for book_text in books[1:]:
#             html_blocks.append(f"<div class='section book'><p>{book_text.strip()}</p></div>")
#     else:
#         html_blocks.append(f"<div class='section'><p>{overview}</p></div>")

#     # Other sections: simply wrap in <div>
#     for sec in ["COMPARATIVE HIGHLIGHTS", "ANOMALIES", "GUIDANCE FOR READERS"]:
#         content = sections.get(sec, "")
#         if content:
#             html_blocks.append(f"<div class='section'><h3>{sec.title()}</h3><p>{content}</p></div>")

#     return "\n".join(html_blocks)




# import json
# import boto3

# ses = boto3.client("ses")
# dynamodb = boto3.resource("dynamodb")
# table = dynamodb.Table("BedrockResults")
# bedrock = boto3.client("bedrock-runtime")  # AWS Bedrock client

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
#     result       = item.get("result", "")
#     prompt       = item.get("prompt", "")
#     input_tokens = int(item.get("input_token", 0))
#     output_tokens= int(item.get("output_token", 0))
#     valid_rows   = int(item.get("valid_row", 0))
#     invalid_rows = int(item.get("invalid_row", 0))

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

#     # ---- Call Bedrock for executive summary (always) ----

#     prompt = """
# Provide an executive summary for the following processed data. 
# Include correlation ID, original prompt, result, token usage, and row counts.
# """

# # Construct text to pass to Bedrock
#     prompt_with_data = f"""{prompt}

#       Correlation ID: {correlation_id}
#       Prompt: {prompt}
#       Result: {result}
#       Tokens → Input: {input_tokens}, Output: {output_tokens}
#       Rows → Valid: {valid_rows}, Invalid: {invalid_rows}
#       """
    
#     # summary = ""
#     # try:
#     #     bedrock_response = bedrock.invoke_model(
#     #         modelId="amazon.nova-micro-v1:0",  # replace with your Bedrock model
#     #         body=json.dumps({
#     #         "messages": [
#     #             {
#     #                 "role": "user",
#     #                 "content": [{"text": prompt_with_data}]
#     #             }
#     #         ]
#     #           }),
#     #         contentType="application/json",
#     #         accept="application/json"
#     #     )
#     #     summary_response = json.loads(bedrock_response["body"].read())
#     #     summary = summary_response.get("summary", "")
#     # except Exception as e:
#     #     print("Bedrock summary call failed:", str(e))
#     #     summary = "Summary unavailable due to Bedrock error."

#     # ---- Build email ----
#     if anomalies:
#         subject = f"⚠️ Anomaly Detected - Correlation ID {correlation_id}"
#         body_html = f"""
#         <html>
#           <head>
#             <style>
#               body {{ font-family: Arial, sans-serif; }}
#               .anomaly {{ color: red; font-weight: bold; }}
#               .section {{ margin-bottom: 12px; }}
#             </style>
#           </head>
#           <body>
#             <h2 class="anomaly">Anomaly Detected in Processing</h2>
#             <p><b>Correlation ID:</b> {correlation_id}</p>

#             <div class="section">
#               <p><b>Issues:</b></p>
#               <ul>
#                 {''.join([f"<li>{a}</li>" for a in anomalies])}
#               </ul>
#             </div>

#             <div class="section">
#               <p><b>Executive Summary:</b> {summary}</p>
#             </div>

#             <div class="section">
#               <p><b>Full Result:</b> {result}</p>
#               <p>Tokens → Input: {input_tokens}, Output: {output_tokens}</p>
#               <p>Rows → Valid: {valid_rows}, Invalid: {invalid_rows}</p>
#             </div>
#           </body>
#         </html>
#         """
#     else:
#         subject = f"✅ Processing Completed - Correlation ID {correlation_id}"
#         body_html = f"""
#         <html>
#           <head>
#             <style>
#               body {{ font-family: Arial, sans-serif; }}
#               .success {{ color: green; font-weight: bold; }}
#               .section {{ margin-bottom: 12px; }}
#             </style>
#           </head>
#           <body>
#             <h2 class="success">Processing Completed Successfully</h2>
#             <p><b>Correlation ID:</b> {correlation_id}</p>

#             <div class="section">
#               <p><b>Executive Summary:</b> {summary}</p>
#             </div>

#             <div class="section">
#               <p><b>Full Result:</b> {result}</p>
#               <p>Tokens → Input: {input_tokens}, Output: {output_tokens}</p>
#               <p>Rows → Valid: {valid_rows}, Invalid: {invalid_rows}</p>
#             </div>
#           </body>
#         </html>
#         """

#     # ---- Send email ----
#     ses.send_email(
#         Source=SOURCE_EMAIL,
#         Destination={"ToAddresses": [DEST_EMAIL]},
#         Message={
#             "Subject": {"Data": subject},
#             "Body": {"Html": {"Data": body_html}}
#         }
#     )

#     return {
#         "status": "success",
#         "correlation_id": correlation_id,
#         "notified_to": DEST_EMAIL,
#         "anomalies_found": anomalies,
#         "executive_summary": summary
#     }
