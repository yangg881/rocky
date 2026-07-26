import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


buckets = [required("TOS_BUCKET_A"), required("TOS_BUCKET_B"), required("TOS_BUCKET_C")]
if len(set(buckets)) != 3:
    raise SystemExit("TOS_BUCKET_A, TOS_BUCKET_B and TOS_BUCKET_C must be three distinct buckets")

client = boto3.client(
    "s3",
    endpoint_url=required("TOS_S3_ENDPOINT"),
    aws_access_key_id=required("TOS_ACCESS_KEY_ID"),
    aws_secret_access_key=required("TOS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("TOS_REGION", "cn-beijing"),
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)

for bucket in buckets:
    try:
        client.head_bucket(Bucket=bucket)
        print(f"Bucket ready: {bucket}")
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code not in {"404", "NoSuchBucket", "NotFound"}:
            raise
        client.create_bucket(Bucket=bucket)
        print(f"Bucket created: {bucket}")

