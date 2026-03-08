"""
setup_dynamo.py — Check and create the pathshala-lessons DynamoDB table.
Run once: python setup_dynamo.py
"""
import os, boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
load_dotenv()

TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "pathshala-lessons")
REGION     = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")

dynamodb = boto3.client(
    "dynamodb",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=REGION,
)

print(f"Checking table '{TABLE_NAME}' in {REGION}...")

try:
    resp = dynamodb.describe_table(TableName=TABLE_NAME)
    status = resp["Table"]["TableStatus"]
    item_count = resp["Table"]["ItemCount"]
    print(f"  ✅ Table EXISTS — status: {status}, items: {item_count}")
except ClientError as e:
    if e.response["Error"]["Code"] == "ResourceNotFoundException":
        print("  ⚠️  Table NOT found — creating now...")
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "lesson_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "lesson_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Wait for table to be active
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=TABLE_NAME)
        print(f"  ✅ Table '{TABLE_NAME}' created successfully!")
    else:
        print(f"  ❌ AWS Error: {e}")
