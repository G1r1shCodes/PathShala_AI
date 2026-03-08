"""
lambda_auth_verify_otp.py — PathShala AI OTP Verification Lambda

Verifies OTP from DynamoDB, creates/updates teacher record,
and returns a simple JWT-like token.

ZERO pip dependencies — uses only stdlib + boto3 (built into Lambda).

Environment variables required:
    DYNAMODB_OTP_TABLE      — DynamoDB table for OTPs (default: PathshalaOTPs)
    DYNAMODB_TEACHER_TABLE  — DynamoDB table for teachers (default: PathshalaTeachers)
    JWT_SECRET              — Secret key for signing tokens (default: pathshala-secret)
    AWS_DEFAULT_REGION      — AWS region (default: ap-south-1)
"""

import json
import logging
import os
import time
import hashlib
import hmac
import base64
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")


def get_stored_otp(phone: str) -> dict:
    """Fetch OTP record from DynamoDB."""
    dynamodb = boto3.client("dynamodb", region_name=REGION)
    table = os.environ.get("DYNAMODB_OTP_TABLE", "PathshalaOTPs")

    result = dynamodb.get_item(
        TableName=table,
        Key={"phone": {"S": phone}}
    )
    item = result.get("Item")
    if not item:
        return None

    return {
        "otp": item["otp"]["S"],
        "ttl": int(item["ttl"]["N"]),
        "attempts": int(item.get("attempts", {}).get("N", "0"))
    }


def increment_attempts(phone: str):
    """Increment failed OTP attempt counter."""
    dynamodb = boto3.client("dynamodb", region_name=REGION)
    table = os.environ.get("DYNAMODB_OTP_TABLE", "PathshalaOTPs")

    dynamodb.update_item(
        TableName=table,
        Key={"phone": {"S": phone}},
        UpdateExpression="SET attempts = attempts + :inc",
        ExpressionAttributeValues={":inc": {"N": "1"}}
    )


def delete_otp(phone: str):
    """Delete OTP after successful verification."""
    dynamodb = boto3.client("dynamodb", region_name=REGION)
    table = os.environ.get("DYNAMODB_OTP_TABLE", "PathshalaOTPs")

    dynamodb.delete_item(
        TableName=table,
        Key={"phone": {"S": phone}}
    )


def get_or_create_teacher(phone: str) -> dict:
    """Get existing teacher or create new record in DynamoDB."""
    dynamodb = boto3.client("dynamodb", region_name=REGION)
    table = os.environ.get("DYNAMODB_TEACHER_TABLE", "PathshalaTeachers")

    # Try to get existing teacher
    result = dynamodb.get_item(
        TableName=table,
        Key={"teacherId": {"S": phone}}
    )

    if result.get("Item"):
        item = result["Item"]
        # Update last login
        dynamodb.update_item(
            TableName=table,
            Key={"teacherId": {"S": phone}},
            UpdateExpression="SET last_login = :ts",
            ExpressionAttributeValues={":ts": {"S": str(int(time.time()))}}
        )
        return {
            "phone": phone,
            "name": item.get("name", {}).get("S", ""),
            "school": item.get("school", {}).get("S", "")
        }
    else:
        # Create new teacher
        dynamodb.put_item(
            TableName=table,
            Item={
                "teacherId":   {"S": phone},
                "phone":       {"S": phone},
                "name":        {"S": ""},
                "school":      {"S": ""},
                "created_at":  {"S": str(int(time.time()))},
                "last_login":  {"S": str(int(time.time()))}
            }
        )
        return {"phone": phone, "name": "", "school": ""}


def generate_token(phone: str) -> str:
    """Generate a simple HMAC-based auth token (phone + expiry signed with secret)."""
    secret = os.environ.get("JWT_SECRET", "pathshala-secret")
    expiry = int(time.time()) + 86400 * 7  # 7 days

    payload = f"{phone}:{expiry}"
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    token = base64.urlsafe_b64encode(f"{payload}:{signature}".encode("utf-8")).decode("utf-8")
    return token


def handler(event, context):
    """
    Lambda handler for POST /auth/verify-otp
    Body: {"phone": "+91XXXXXXXXXX", "otp": "1234"}
    """
    try:
        body = json.loads(event.get("body", "{}"))
        phone = body.get("phone", "").strip()
        otp = body.get("otp", "").strip()

        # Validate input
        if not phone or not otp:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": False,
                    "error": "MISSING_FIELDS",
                    "message": "Phone and OTP are required"
                })
            }

        # Fetch stored OTP
        stored = get_stored_otp(phone)
        if not stored:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": False,
                    "error": "NO_OTP_FOUND",
                    "message": "No OTP found for this number. Please request a new OTP."
                })
            }

        # Check expiry
        if time.time() > stored["ttl"]:
            delete_otp(phone)
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": False,
                    "error": "OTP_EXPIRED",
                    "message": "OTP has expired. Please request a new one."
                })
            }

        # Check max attempts (5)
        if stored["attempts"] >= 5:
            delete_otp(phone)
            return {
                "statusCode": 429,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": False,
                    "error": "TOO_MANY_ATTEMPTS",
                    "message": "Too many failed attempts. Please request a new OTP."
                })
            }

        # Verify OTP
        if otp != stored["otp"]:
            increment_attempts(phone)
            remaining = 4 - stored["attempts"]
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": False,
                    "error": "INVALID_OTP",
                    "message": f"Invalid OTP. {remaining} attempts remaining."
                })
            }

        # OTP verified — clean up and create session
        delete_otp(phone)
        teacher = get_or_create_teacher(phone)
        token = generate_token(phone)

        logger.info(f"Teacher {phone} verified successfully")

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "message": "OTP verified successfully",
                "token": token,
                "teacher": teacher
            })
        }

    except Exception as e:
        logger.exception("Error in verify-otp handler")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": str(e)
            })
        }
