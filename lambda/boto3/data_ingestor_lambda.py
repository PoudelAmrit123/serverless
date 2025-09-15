

import boto3
import csv
import io
import json
import uuid
from datetime import datetime , timezone

s3_client = boto3.client("s3")

## Targeting the History Category as the dataset is large.
## Can Target another topic also..
TARGET_SUB_CATEGORY = "History" 

## Dropping the Column that seems unnecesary in this context.
COLUMNS_TO_DROP = {
    'descriptionRaw', 'sku', 'style', 'url', 'variants',
    'gtin', 'mpn', 'scrapedDate', 'imageUrls', 'new_path',
    'weight_rawUnit', 'weight_unit', 'weight_value'
}


REQUIRED_COLS = ['name', 'salePrice', 'rating', 'reviewCount']


# logging to send to cloudwatch
def log_json(message, correlation_id, **kwargs):
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlationId": correlation_id,
        "message": message,
        **kwargs
    }
    print(json.dumps(log_entry))


# cleaning the data to more 
def clean_row(row: dict) -> dict:
    # Strip whitespace
    row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

    # Replace empty-like tokens with None
    empty_tokens = {'', ' ', 'NaN', 'nan', 'None', 'NULL', 'null'}
    row = {k: (None if v in empty_tokens else v) for k, v in row.items()}

    # Convert numeric fields
    for c in ['salePrice', 'listedPrice', 'rating', 'reviewCount']:
        if c in row and row[c] is not None:
            try:
                row[c] = float(row[c])
            except ValueError:
                row[c] = None

    # Drop unwanted columns
    row = {k: v for k, v in row.items() if k not in COLUMNS_TO_DROP}

    return row


# ------------VALIDATION OF DATA -----------
def validate_data(rows):
    selected_rows, rejected_rows = [], []

    for row in rows:
        missing_fields = [col for col in REQUIRED_COLS if not row.get(col)]
        if missing_fields:
            row["rejectionReason"] = f"Missing required fields: {', '.join(missing_fields)}"
            rejected_rows.append(row)
        else:
            selected_rows.append(row)

    return selected_rows, rejected_rows


#  ETAG For Idempotent
def get_last_processed_etag(bucket, processed_key):
    try:
        resp = s3_client.head_object(Bucket=bucket, Key=processed_key)
        return resp["Metadata"].get("source-etag")
    except s3_client.exceptions.ClientError:
        return None


#  output writing to the 
def write_outputs(selected_rows, rejected_rows, bucket, correlation_id, source_etag , total_rows , valid_count , invalid_count):
    outputs = {
        "processed/selected_data.json": json.dumps(selected_rows, ensure_ascii=False, indent=2),
        "rejects/rejected_data.json": json.dumps(rejected_rows, ensure_ascii=False, indent=2),
    }
#writing metadata for analyzer function
    metadata_base = {
        "correlation_id": correlation_id,
        "source-etag": source_etag,
        "total_rows": str(total_rows),
        "valid_count": str(valid_count),
        "invalid_count": str(invalid_count),
    }

    for s3_key, content in outputs.items():
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=content.encode("utf-8"),
            ContentType="application/json",
            Metadata= metadata_base
        )
        log_json("File written", correlation_id, file=s3_key,
                 rows=len(selected_rows) if "selected" in s3_key else len(rejected_rows))


## main function 
def lambda_handler(event, context):
    correlation_id = str(uuid.uuid4())
    log_json("Lambda started", correlation_id, event=event)

    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]

    # 1. Get current ETag
    head = s3_client.head_object(Bucket=bucket, Key=key)
    current_etag = head["ETag"].strip('"')

    # 2. Check last processed etag
    last_etag = get_last_processed_etag(bucket, "processed/selected_data.json")
    if last_etag == current_etag:
        log_json("Input file unchanged — skipping", correlation_id, etag=current_etag)
        return {"status": "skipped", "correlationId": correlation_id}

    # 3. Read CSV dataset
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    rows = []
    with io.StringIO(obj["Body"].read().decode("utf-8")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = clean_row(row)
            rows.append(row)

    # 4. Filter category 

    candidate_rows_len = [r for r in rows if r.get("nodeName")]
    total_rows = len(candidate_rows_len)
    candidate_rows = [r for r in rows if r.get("nodeName") and TARGET_SUB_CATEGORY in r["nodeName"]]

    if not candidate_rows:
        log_json("No matching rows for target category — nothing to process",
                 correlation_id, target=TARGET_SUB_CATEGORY)
        return {"status": "no_category_match", "correlationId": correlation_id}

    # 5. Validate
    selected_rows, rejected_rows = validate_data(candidate_rows)
    valid_count = len(selected_rows)
    invalid_count = len(rejected_rows)

    log_json("Validation complete", correlation_id,
             selected=len(selected_rows), rejected=len(rejected_rows))

    # 6. Save results
    write_outputs(selected_rows, rejected_rows, bucket, correlation_id, current_etag , total_rows , valid_count , invalid_count)

    log_json("Validation complete", correlation_id,
             totalRows=total_rows,
             valid=valid_count,
             invalid=invalid_count)
    return {"status": "success", "correlationId": correlation_id}





