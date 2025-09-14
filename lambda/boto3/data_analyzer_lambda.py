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

    # Only process the selected_data.json file
    if not key.endswith("processed/selected_data.json"):
        print(f"Skipping key {key}, not the target file.")
        return {"status": "skipped", "correlation_id": correlation_id, "key": key}

    # Fetch JSON file from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    metadata = response.get("Metadata", {})

    correlation_id = metadata.get("correlation_id", str(uuid.uuid4()))
    # total_rows = int(metadata.get("total_rows", 0))
    valid_count = int(metadata.get("valid_count", 0))
    invalid_count = int(metadata.get("invalid_count", 0))
    total_rows = valid_count + invalid_count
    content = response['Body'].read().decode('utf-8')
    data = json.loads(content)

    # Construct prompt
    # prompt = f"Provide me the best audobook which is less then 5 dollar in price and have the rating of more than 4.5:\n{json.dumps(data, indent=2)}"

    # prompt = "Provide me the best audiobook which is less than 5 dollar in price and have a rating of more than 4.5."
    # prompt_with_data = f"{prompt}\n{json.dumps(data, indent=2)}"

    # # Call Bedrock correctly
    # bedrock_response = bedrock.invoke_model(
    #     modelId="amazon.nova-micro-v1:0",
    #     contentType="application/json",
    #     accept="application/json",
    #     body=json.dumps({
    #         "messages": [
    #             {
    #                 "role": "user",
    #                 "content": [
    #                     {"text": prompt_with_data}
    #                 ]
    #             }
    #         ]
    #     })
    # )


    # prompt = "Provide me the best audiobook which is less than $5 in price and has a rating above 4.5."

    
    # data_context = f"""
    # You are given a dataset in JSON format. Only use this dataset to answer.

    # Dataset:
    # {json.dumps(data, indent=2)}

    # Task:
    # {prompt}
    # """

    # bedrock_response = bedrock.invoke_model(
    #     modelId="amazon.nova-micro-v1:0",
    #     contentType="application/json",
    #     accept="application/json",
    #     body=json.dumps({
    #         "messages": [
             
    #             {
    #                 "role": "user",
    #                 "content": [{"text": (
    #                 "You are a data analysis assistant. Only use the provided dataset to answer. "
    #                 "Do not rely on outside knowledge.\n\n"
    #                 f"{data_context}"
    #             )}]
    #             }
    #         ]
    #     })
    # )



    filtered_rows = [
        {
            "name": r.get("name"),
            "salePrice": r.get("salePrice"),
            "rating": r.get("rating"),
            "description" : r.get("description"),
            # "additionalProperties": r.get("additionalProperties"),
            "name": r.get("name")
        }
        for r in data[:10]  # top 20 rows only, adjust as needed
    ]

    # Clear, grounded prompt
    # prompt = """
    # Find the salesprice  , listedPrice of the book that have this 'ECPA Bestseller\n\nAcross forty days of vivid storytelling, It Is Finished of…uestion that can change your life, Lord, why me' in the descritpion field.
    # Say "Not available is not found"
    # """

    prompt = """
    
    according to the given data which book is the best one among 
    'Great Battles for Boys The American Revolutionse' and 
    'Gödel, Escher, Bach: An Eternal Golden Braid'  if i am new to the histroy mind its price its rating  and easiyne to the people who are new to the history book.
    
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





    # Parse response
    result = json.loads(bedrock_response['body'].read().decode('utf-8'))
    insights = result["output_text"] if "output_text" in result else result 

    

    #############################
    ### For Summary #############
    #############################




    


    summary = extract_summary(insights)
    usage = extract_usage(insights)
    input_token = usage["input_tokens"]
    output_token = usage["output_tokens"]

    # Save response back to S3
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


