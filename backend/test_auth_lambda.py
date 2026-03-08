import os
import json
import logging
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv('.env')

logging.basicConfig(level=logging.INFO)
import lambda_auth_request_otp as l

# Use the WhatsApp from number as the SMS from number for testing
# (Assuming the Twilio number can send SMS)
os.environ['TWILIO_SMS_FROM'] = os.environ.get('TWILIO_WHATSAPP_FROM', '').replace('whatsapp:', '')
test_phone = os.environ.get('TWILIO_WHATSAPP_TO', '').replace('whatsapp:', '')

print(f"Testing SMS to: {test_phone}")
print(f"From Twilio number: {os.environ['TWILIO_SMS_FROM']}")

event = {
    "body": json.dumps({"phone": test_phone})
}

try:
    response = l.handler(event, None)
    print("\nLambda Response:")
    print(json.dumps(response, indent=2))
except Exception as e:
    print(f"Error test failed: {e}")
