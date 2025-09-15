import json
import boto3
import uuid
from datetime import datetime, timezone

s3_client = boto3.client("s3")
eventbridge = boto3.client("events")
bedrock = boto3.client("bedrock-runtime")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("BedrockResults")

def lambda_handler(event, context):
    timestamp = datetime.now(timezone.utc).isoformat()
    correlation_id = str(uuid.uuid4())
    print("Received event:", json.dumps(event))

    # Handle EventBridge event
    if "detail" in event:
        bucket_name = event["detail"]["bucket"]["name"]
        key = event["detail"]["object"]["key"]

    # Handle direct S3 notification event
    elif "Records" in event:
        bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
        key = event["Records"][0]["s3"]["object"]["key"]

    else:
        raise ValueError("Unsupported event format: no detail or Records found")

    # Only process the selected_data.json file that come from data ingestor lambda function
    if not key.endswith("processed/selected_data.json"):
        print(f"Skipping key {key}, not the target file.")
        return {"status": "skipped", "correlation_id": correlation_id, "key": key}

    # Fetch  file from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    metadata = response.get("Metadata", {})

 ## Get the Correlation ID and Count.
    correlation_id = metadata.get("correlation_id", str(uuid.uuid4()))
  
    valid_count = int(metadata.get("valid_count", 0))
    invalid_count = int(metadata.get("invalid_count", 0))
    total_rows = valid_count + invalid_count 
    content = response['Body'].read().decode('utf-8')
    data = json.loads(content)



  ##  the limited rows from the dataset as the llm is not being able to handle

    filtered_rows = [
        {
            "name": r.get("name"),
            "salePrice": r.get("salePrice"),
            "rating": r.get("rating"),
            "description" : r.get("description"),
            # "additionalProperties": r.get("additionalProperties"),
            "name": r.get("name")
        }
        for r in data[:10]  
    ]

    # Clear, grounded prompt
    # prompt = """
    # Find the salesprice  , listedPrice of the book that have this 'ECPA Bestseller\n\nAcross forty days of vivid storytelling, It Is Finished of…uestion that can change your life, Lord, why me' in the descritpion field.
    # Say "Not available is not found"
    # """

    # prompt = """
    
    # according to the given data which book is the best one among 
    # 'Great Battles for Boys The American Revolutionse' and 
    # 'Gödel, Escher, Bach: An Eternal Golden Braid'  if i am new to the histroy mind its price its rating  and easiyne to the people who are new to the history book.
    
    # """


    user_request= "Show me all books with price >= 20 and rating < 4.0"



    prompt = f"""
You are a historian and educational reviewer. You are given structured JSON data about books in history, anthropology, and related fields. 
Your task has two modes:
1. **Structured Analysis Mode** (default)  
If no direct filter question is asked, Organize your analysis into the following sections:

OVERVIEW OF BOOKS  
Give a short narrative description for each book, including its subject focus, author expertise, target readership, and relevance in the field. Keep it clear and concise.  

COMPARATIVE HIGHLIGHTS  
Discuss how the books differ and overlap in readability for newcomers, scholarly depth, affordability (prices), and popularity (ratings/reviews).  

Ananomalies 
Include this section only if something unusual stands out (e.g., exceptionally high/low price, unique bestseller rank, extraordinary ratings, or niche specialization).  
If no such cases exist, omit this section entirely.  

GUIDANCE FOR READERS  
Offer 2–3 clear takeaways:  
- Which book a beginner should start with,  
- Which book is more suitable for advanced or academic readers,  
- Which book offers the best balance of value and quality.  

Return your answer as plain text, beginning each section with its heading in uppercase.  
Do not include any extra sections beyond these.

---

Example Output Format:

OVERVIEW OF BOOKS  
"Laboratory Manual and Workbook for Biological Anthropology" provides hands-on exercises for students learning biological anthropology. Written by experienced educators, it is especially aimed at undergraduates and newcomers to the field.  
"The Organization of Information" introduces principles of cataloging and metadata, written by seasoned library science scholars. It is designed for library professionals and students in information science.  

COMPARATIVE HIGHLIGHTS  
The anthropology manual emphasizes practical engagement and is easier for beginners, while the library science text is more theoretical and suited to professional training.  
Both books are highly rated (4.6 vs 4.5), but the anthropology manual has more reviews, suggesting broader adoption.  
Price-wise, they are in a similar range, though the anthropology manual is slightly higher.  

Anomalies
The library science book ranks #1 in its subcategory (Cataloging), marking it as a definitive reference in that area.  

GUIDANCE FOR READERS  
For newcomers to anthropology: start with "Laboratory Manual and Workbook for Biological Anthropology" for its structured exercises.  
For advanced learners or professionals in information science: "The Organization of Information" offers deeper theoretical grounding.  
For best balance of price and quality: "The Organization of Information" is slightly cheaper but nearly equal in quality.  



2. **Direct Query Mode**  
   If the user explicitly asks for a filtered condition (e.g., "Suggest me books with price over 50 and rating under 4.2"),  
   skip the structured sections and directly return the exact matching books in a simple list format: 

   If no matches are found, respond: "i'm sorry, but i can't provide specific details" 

   The user request is {user_request}

   Example:  
   Books matching your request:  
   - Title: "Book A", Price: 55.0, Rating: 4.0  
   - Title: "Book B", Price: 62.5, Rating: 3.8 

   
"""


    prompt_with_data = f"{prompt}\n\nDataset:\n{json.dumps(filtered_rows, indent=2)}"

    bedrock_response = bedrock.invoke_model(
        modelId="amazon.nova-micro-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt_with_data}]
                }
            ]
        })
    )





    # Parsing the response
    print("the bedrock response is " , bedrock_response)
    result = json.loads(bedrock_response['body'].read().decode('utf-8'))
    insights = result["output_text"] if "output_text" in result else result 

       


    summary = extract_summary(insights)
    usage = extract_usage(insights)
    input_token = usage["input_tokens"]
    output_token = usage["output_tokens"]

    # Save response back to S3 later remove that.
    output_key = "processed/bedrock_response.json"
    s3_client.put_object(
        Bucket=bucket_name,
        Key=output_key,
        Body=json.dumps(insights, ensure_ascii=False, indent=2).encode("utf-8")
    )

    table.put_item(
        Item={
            "correlation_id": correlation_id,
            "Timestamp": timestamp,
            "prompt": prompt,   
            "insights": insights ,
            "total_row": total_rows,
            "valid_row": valid_count,
            "invalid_row": invalid_count ,
            "result": summary,
            "input_token": input_token,
            "output_token": output_token
        }
    )

    eventbridge.put_events(
    Entries=[{
        "Source": "my.data.analyzer",
        "DetailType": "DataAnalysisCompleted",
        "Detail": json.dumps({
            "correlation_id": correlation_id,
            "s3_bucket": bucket_name,
            "s3_key": output_key,
            "timestamp": timestamp
        }),
        "EventBusName": "default"
    }]
)

    return {
        "status": "success",
        "correlation_id": correlation_id,
        "s3_output": output_key 
    }



def extract_summary(response_json):
    try:
        content_list = (
            response_json.get("output", {})
            .get("message", {})
            .get("content", [])
        )

        texts = []
        for item in content_list:
            text_val = item.get("text")
            if text_val:
                texts.append(text_val)

        return "\n".join(texts) if texts else None
    except Exception as e:
        print("Error in extract_summary:", e)
        return None
    
def extract_usage(response_json):
    try:
        usage = response_json.get("usage", {})

        return {
            "input_tokens": usage.get("inputTokens"),
            "output_tokens": usage.get("outputTokens"),
            
        }
    except Exception as e:
        print("Error in extract_usage:", e)
        return None


