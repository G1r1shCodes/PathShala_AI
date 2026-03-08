"""
lambda_auth_request_otp.py — PathShala AI OTP Request Lambda

Generates a 4-digit OTP, stores it in DynamoDB with 5-min TTL,
and sends it to the teacher's phone via Twilio SMS.

ZERO pip dependencies — uses only stdlib + boto3 (built into Lambda).

Environment variables required:
    TWILIO_ACCOUNT_SID   — Twilio account SID
    TWILIO_AUTH_TOKEN    — Twilio auth token
    TWILIO_SMS_FROM      — Twilio phone number (e.g. +1xxxxxxxxxx)
    DYNAMODB_OTP_TABLE   — DynamoDB table name (default: PathshalaOTPs)
    AWS_DEFAULT_REGION   — AWS region (default: ap-south-1)
"""

import json
import logging
import os
import random
import time
import urllib.request
import urllib.parse
import base64
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def send_sms_twilio(phone: str, otp: str):
    """Send OTP via Twilio SMS using pure REST (no pip dependency)."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_num = os.environ.get("TWILIO_SMS_FROM", "")

    if not sid or not token or not from_num:
        logger.error("Twilio credentials not configured")
        raise ValueError("Twilio SMS credentials not configured")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    body = f"Your PathShala AI login OTP is: {otp}\nValid for 5 minutes.\n\nDo not share this code."
    data = urllib.parse.urlencode({
        "From": f"whatsapp:{from_num}" if not from_num.startswith("whatsapp:") else from_num,
        "To": f"whatsapp:{phone}" if not phone.startswith("whatsapp:") else phone,
        "Body": body
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data)
    auth = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("utf-8")
    req.add_header("Authorization", f"Basic {auth}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req) as response:
        status = response.status
        logger.info(f"Twilio SMS sent to {phone}, status: {status}")
        return status


def store_otp(phone: str, otp: str):
    """Store OTP in DynamoDB with 5-minute TTL."""
    dynamodb = boto3.client("dynamodb", region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"))
    table = os.environ.get("DYNAMODB_OTP_TABLE", "PathshalaOTPs")
    ttl = int(time.time()) + 300  # 5 minutes

    dynamodb.put_item(
        TableName=table,
        Item={
            "phone":      {"S": phone},
            "otp":        {"S": otp},
            "created_at": {"N": str(int(time.time()))},
            "ttl":        {"N": str(ttl)},
            "attempts":   {"N": "0"}
        }
    )
    logger.info(f"OTP stored for {phone}, expires at TTL={ttl}")


def handler(event, context):
    """
    Lambda handler for POST /auth/request-otp
    Body: {"phone": "+91XXXXXXXXXX"}
    """
    try:
        body = json.loads(event.get("body", "{}"))
        phone = body.get("phone", "").strip()

        # Validate phone
        if not phone or not phone.startswith("+") or len(phone) < 12:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "success": False,
                    "error": "INVALID_PHONE",
                    "message": "Please provide a valid phone number with country code (e.g. +91XXXXXXXXXX)"
                })
            }

        # Check for rate-limiting (Cooldown of 60 seconds)
        dynamodb = boto3.client("dynamodb", region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"))
        table = os.environ.get("DYNAMODB_OTP_TABLE", "PathshalaOTPs")
        
        try:
            response = dynamodb.get_item(TableName=table, Key={"phone": {"S": phone}})
            if "Item" in response:
                last_request_time = int(response["Item"]["created_at"]["N"])
                current_time = int(time.time())
                
                # If less than 60 seconds have passed, block the request
                if current_time - last_request_time < 60:
                    logger.warning(f"Rate limit hit for {phone}. Cooldown active.")
                    return {
                        "statusCode": 429,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({
                            "success": False,
                            "error": "TOO_MANY_REQUESTS",
                            "message": "Please wait 60 seconds before requesting another OTP."
                        })
                    }
        except Exception as e:
            logger.error(f"Failed to check rate limit in DynamoDB: {e}")

        # Generate 4-digit OTP
        otp = str(random.randint(1000, 9999))
        logger.info(f"Generated OTP for {phone}")

        # Store in DynamoDB
        store_otp(phone, otp)

        # Send via Twilio SMS
        send_sms_twilio(phone, otp)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "message": "OTP sent successfully",
                "phone": phone,
                "expiresIn": 300
            })
        }

    except Exception as e:
        logger.exception("Error in request-otp handler")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": "INTERNAL_ERROR",
                "message": str(e)
            })
        }
