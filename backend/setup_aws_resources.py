import os
import boto3
import json
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# We need to make sure the bucket name is unique globally in AWS, so if you already have one, use it.
# Otherwise, we will append a random string or let you define it in .env
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "pathshala-curriculum-unique-name-1234") 
DYNAMO_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "pathshala-lessons")
REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")

def get_aws_clients():
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=REGION
    )
    s3_client = session.client('s3')
    dynamodb = session.resource('dynamodb')
    return s3_client, dynamodb

def setup_s3(s3_client):
    print(f"Creating S3 bucket: {BUCKET_NAME} in region {REGION}...")
    try:
        if REGION == 'us-east-1':
            s3_client.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3_client.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
        
        # Turn off block public access so we can make public audio objects for Twilio
        s3_client.put_public_access_block(
            Bucket=BUCKET_NAME,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        print(f"✅ S3 Bucket '{BUCKET_NAME}' created successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] in ('BucketAlreadyExists', 'BucketAlreadyOwnedByYou'):
            print(f"✅ S3 Bucket '{BUCKET_NAME}' already exists.")
        else:
            print(f"❌ Error creating S3 bucket: {e}")
            return

    # Upload ncert.json
    try:
        s3_client.upload_file("ncert.json", BUCKET_NAME, "ncert.json")
        print(f"✅ ncert.json uploaded to s3://{BUCKET_NAME}/ncert.json")
    except Exception as e:
        print(f"❌ Error uploading ncert.json: {e}")

def setup_dynamodb(dynamodb):
    print(f"Creating DynamoDB table: {DYNAMO_TABLE_NAME}...")
    try:
        table = dynamodb.create_table(
            TableName=DYNAMO_TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'lesson_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'lesson_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        # Wait until the table exists.
        print("Waiting for table to be created... this may take a moment.")
        table.meta.client.get_waiter('table_exists').wait(TableName=DYNAMO_TABLE_NAME)
        print(f"✅ DynamoDB table '{DYNAMO_TABLE_NAME}' created successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"✅ DynamoDB table '{DYNAMO_TABLE_NAME}' already exists.")
        else:
            print(f"❌ Error creating DynamoDB table: {e}")

def setup():
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        print("❌ AWS Credentials not found in .env! Please add them before running this script.")
        return
        
    print("🔑 AWS credentials found. Starting setup...")
    try:
        s3_client, dynamodb = get_aws_clients()
        
        print("\n--- Setting up S3 ---")
        setup_s3(s3_client)
        
        print("\n--- Setting up DynamoDB ---")
        setup_dynamodb(dynamodb)
        
        print("\n🎉 AWS Setup Complete! You're ready to proceed with the PRD v2 implementation.")
        print(f"👉 Please make sure S3_BUCKET_NAME={BUCKET_NAME} is set in your .env")
        
    except Exception as e:
        print(f"❌ Unexpected error during setup: {e}")

if __name__ == "__main__":
    setup()
