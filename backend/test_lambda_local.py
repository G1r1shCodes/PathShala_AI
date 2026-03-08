import os
import json
from dotenv import load_dotenv

# Load local .env so the handler has credentials
load_dotenv()

from lambda_generate import handler

print("🚀 Simulating AWS API Gateway invocation for lambda_generate.py...")

# Create a mock AWS API Gateway event
mock_event = {
    "body": json.dumps({
        "transcript": "Class 4 English verbs",
        "whatsapp_number": "6369631956"
    })
}

try:
    response = handler(mock_event, context=None)
    print("\n✅ Lambda Response Code:", response.get("statusCode"))
    print("✅ Headers:", response.get("headers"))
    if "body" in response:
        body_data = json.loads(response["body"])
        print("\n✅ Response Body (parsed):")
        print(json.dumps(body_data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"\n❌ Error during execution: {e}")
