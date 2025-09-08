import boto3
import pandas as pd
import numpy as np
import io
import json
import uuid
from datetime import datetime

s3_client = boto3.client("s3")

# ---------- CONFIG ----------
TARGET_SUB_CATEGORY = "Biographies & Memoirs"
COLUMNS_TO_DROP = [
    'descriptionRaw', 'sku', 'style', 'url', 'variants',
    'gtin', 'mpn', 'scrapedDate', 'imageUrls', 'new_path',
    'weight_rawUnit', 'weight_unit', 'weight_value', 'new_path'
]
REQUIRED_COLS = ['name', 'salePrice', 'rating', 'reviewCount']


# ---------- LOGGING ----------
def log_json(message, correlation_id, **kwargs):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "correlationId": correlation_id,
        "message": message,
        **kwargs
    }
    print(json.dumps(log_entry))


# ---------- CLEAN ----------
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['nodeName'] = df['nodeName'].astype(str).str.strip()

    # Replace empty tokens with NaN
    empty_tokens = ['', ' ', 'NaN', 'nan', 'None', 'NULL', 'null']
    df.replace(to_replace=empty_tokens, value=np.nan, inplace=True)

    # Force numeric conversion
    for c in ['salePrice', 'listedPrice', 'rating', 'reviewCount']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Drop unwanted cols + drop all-null columns
    df.drop(columns=[c for c in COLUMNS_TO_DROP if c in df.columns],
            inplace=True, errors='ignore')
    df.dropna(axis=1, how='all', inplace=True)

    return df


# ---------- VALIDATE ----------
def validate_data(df: pd.DataFrame):
    selected_rows, rejected_rows = [], []

    for _, row in df.iterrows():
        missing_fields = [col for col in REQUIRED_COLS if pd.isna(row.get(col))]
        row_dict = row.to_dict()
        if missing_fields:
            row_dict["rejectionReason"] = f"Missing required fields: {', '.join(missing_fields)}"
            rejected_rows.append(row_dict)
        else:
            selected_rows.append(row_dict)

    return selected_rows, rejected_rows


# ---------- ETAG TRACKING ----------
def get_last_processed_etag(bucket, processed_key):
    try:
        resp = s3_client.head_object(Bucket=bucket, Key=processed_key)
        return resp["Metadata"].get("source-etag")
    except s3_client.exceptions.ClientError:
        return None


# ---------- OUTPUT ----------
def write_outputs(selected_rows, rejected_rows, bucket, correlation_id, source_etag):
    outputs = {
        "processed/selected/selected_data.json": json.dumps(selected_rows, ensure_ascii=False, indent=2),
        "processed/rejected/rejected_data.json": json.dumps(rejected_rows, ensure_ascii=False, indent=2),
    }

    for s3_key, content in outputs.items():
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=content.encode("utf-8"),
            ContentType="application/json",
            Metadata={"source-etag": source_etag}
        )
        log_json("File written", correlation_id, file=s3_key,
                 rows=len(selected_rows) if "selected" in s3_key else len(rejected_rows))


# ---------- MAIN ----------
def lambda_handler(event, context):
    correlation_id = str(uuid.uuid4())
    log_json("Lambda started", correlation_id, event=event)

    bucket = event["bucket"]
    key = event["key"]

    # 1. Get current ETag
    head = s3_client.head_object(Bucket=bucket, Key=key)
    current_etag = head["ETag"].strip('"')

    # 2. Check last processed etag
    last_etag = get_last_processed_etag(bucket, "processed/selected/selected_data.json")
    if last_etag == current_etag:
        log_json("Input file unchanged — skipping", correlation_id, etag=current_etag)
        return {"status": "skipped", "correlationId": correlation_id}

    # 3. Read dataset
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(io.BytesIO(obj["Body"].read()))

    # 4. Clean
    df = clean_data(df)

    # 5. Filter category FIRST
    candidate_df = df[df['nodeName'].str.contains(TARGET_SUB_CATEGORY, na=False)].copy().reset_index(drop=True)

    if candidate_df.empty:
        log_json("No matching rows for target category — nothing to process",
                 correlation_id, target=TARGET_SUB_CATEGORY)
        return {"status": "no_category_match", "correlationId": correlation_id}

    # 6. Validate
    selected_rows, rejected_rows = validate_data(candidate_df)

    log_json("Validation complete", correlation_id,
             selected=len(selected_rows), rejected=len(rejected_rows))

    # 7. Save results (JSON only)
    write_outputs(selected_rows, rejected_rows, bucket, correlation_id, current_etag)

    log_json("Lambda finished", correlation_id)
    return {"status": "success", "correlationId": correlation_id}
