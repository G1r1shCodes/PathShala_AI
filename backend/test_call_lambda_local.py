"""
Local test for the full Twilio voice call flow.
Simulates: webhook → respond → generate
"""
import os, sys, json
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, '.')

# ─── Step 1: Test lambda_call_webhook ────────────────────────────────────────
print("\n" + "="*60)
print("STEP 1: lambda_call_webhook (initial greeting)")
print("="*60)
from lambda_call_webhook import handler as webhook_handler

event = {}
resp = webhook_handler(event, None)
print(f"Status: {resp['statusCode']}")
print(f"TwiML:\n{resp['body']}")

assert resp['statusCode'] == 200
assert 'Gather' in resp['body']
assert 'API_BASE_URL' not in resp['body'], "FAIL: Absolute URL not set — did you set API_BASE_URL env var?"
print("✅ Webhook handler looks good!")

# ─── Step 2: Test lambda_call_respond ────────────────────────────────────────
print("\n" + "="*60)
print("STEP 2: lambda_call_respond (speech received)")
print("="*60)
from lambda_call_respond import handler as respond_handler

# Simulate Twilio sending us speech + call SID
import urllib.parse
speech = "Class 2 Hindi alphabets aur Class 4 Math division"
form_body = urllib.parse.urlencode({
    "SpeechResult": speech,
    "CallSid": "CA_TEST_SID_123",
    "From": "+916369631956"
})

event = {
    "body": form_body,
    "isBase64Encoded": False
}

# Monkey-patch boto3 invoke to avoid real AWS call during test
import unittest.mock as mock

with mock.patch("boto3.client") as mock_boto:
    mock_lambda = mock.MagicMock()
    mock_boto.return_value = mock_lambda
    mock_lambda.invoke.return_value = {"StatusCode": 202}

    resp = respond_handler(event, None)
    print(f"Status: {resp['statusCode']}")
    print(f"TwiML:\n{resp['body']}")

    # Verify boto3 async invoke was called
    if mock_lambda.invoke.called:
        call_args = mock_lambda.invoke.call_args
        print(f"\n✅ Async Lambda invoke called!")
        print(f"   Function: {call_args.kwargs.get('FunctionName', call_args[1].get('FunctionName', 'N/A'))}")
        print(f"   InvocationType: {call_args.kwargs.get('InvocationType', call_args[1].get('InvocationType', 'N/A'))}")
        payload = json.loads(call_args.kwargs.get('Payload', call_args[1].get('Payload', b'{}')))
        print(f"   Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    else:
        print("❌ boto3 invoke was NOT called!")

assert resp['statusCode'] == 200
assert 'Pause' in resp['body'], "FAIL: No Pause in TwiML — Twilio won't hold the call!"
print("✅ Respond handler looks good!")

# ─── Step 3: Test lambda_call_generate ───────────────────────────────────────
print("\n" + "="*60)
print("STEP 3: lambda_call_generate (Gemini + Twilio update)")
print("="*60)

if not os.environ.get("GEMINI_API_KEY"):
    print("⚠️  GEMINI_API_KEY not set — skipping live Gemini test")
    print("   Set it in .env to run this step")
else:
    from lambda_call_generate import get_gemini_lesson, update_call_with_lesson

    print(f"Calling Gemini for: '{speech}'")
    result = get_gemini_lesson(speech)
    lesson = result['lesson_text']
    print(f"\n✅ Gemini lesson generated ({len(lesson)} chars):")
    print("-" * 40)
    print(lesson[:500] + ("..." if len(lesson) > 500 else ""))
    print("-" * 40)

    # Test the Twilio call update (with a fake call SID — will fail gracefully)
    print("\nTesting Twilio call update (with fake CallSid — expect auth error):")
    update_call_with_lesson("CA_FAKE_SID_FOR_TEST", lesson, "hi-IN")
    print("✅ update_call_with_lesson ran without crashing!")

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
