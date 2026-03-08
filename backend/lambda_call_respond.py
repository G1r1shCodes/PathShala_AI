import json
import logging
import os
import urllib.parse
import re
import base64
import boto3
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def detect_language(text: str) -> str:
    devanagari = re.compile(r'[\u0900-\u097F]')
    return "hi" if devanagari.search(text) else "en"


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Standalone Lambda handler for the Twilio /call-webhook/respond action.
    
    Strategy to beat Twilio's 15-second timeout:
    1. Extract CallSid + SpeechResult from the Twilio POST body.
    2. Invoke lambda_call_generate ASYNCHRONOUSLY (fire-and-forget).
    3. Return TwiML that pauses the call for up to 40 seconds so Twilio
       doesn't hang up while Gemini is thinking.
    4. lambda_call_generate will update the live call via Twilio REST API
       once the lesson is ready.
    """
    try:
        body_str = event.get("body", "")
        if event.get("isBase64Encoded"):
            body_str = base64.b64decode(body_str).decode("utf-8")

        parsed_body = urllib.parse.parse_qs(body_str)
        speech_result = parsed_body.get("SpeechResult", [""])[0]
        call_sid = parsed_body.get("CallSid", [""])[0]
        # Twilio sends the caller's number in the "From" field e.g. "+916369631956"
        caller_number = parsed_body.get("From", [""])[0]

        logger.info(f"CallSid={call_sid} | From={caller_number} | Speech='{speech_result}'")

        base_url = os.environ.get("API_BASE_URL", "").rstrip("/")
        gather_action = f"{base_url}/call-webhook/respond"

        # ── Empty speech: re-prompt ──────────────────────────────────────────
        if not speech_result or not speech_result.strip():
            logger.warning("Empty SpeechResult — re-prompting caller")
            twiml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Response>'
                f'<Gather input="speech" action="{gather_action}" timeout="5" speechTimeout="auto" language="hi-IN">'
                '<Say language="hi-IN">Kripaya apna lesson request boliye.</Say>'
                '</Gather>'
                '</Response>'
            )
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/xml"},
                "body": twiml
            }

        # ── Detect language for wait message ─────────────────────────────────
        lang_code = detect_language(speech_result)
        if lang_code == "hi":
            wait_msg = "आपका lesson plan तैयार हो रहा है। कृपया रुकें।"
            wait_lang = "hi-IN"
        else:
            wait_msg = "Your lesson plan is being prepared. Please stay on the line."
            wait_lang = "en-IN"

        # ── Fire-and-forget: invoke lambda_call_generate async ───────────────
        generate_fn = os.environ.get("LAMBDA_CALL_GENERATE_NAME", "pathshala-call-generate")
        try:
            lambda_client = boto3.client("lambda", region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"))
            payload = {
                "call_sid": call_sid,
                "speech_result": speech_result,
                "lang_code": lang_code,
                "tts_lang": "hi-IN" if lang_code == "hi" else "en-US",
                "caller_number": caller_number   # forward caller's number for WhatsApp delivery
            }
            lambda_client.invoke(
                FunctionName=generate_fn,
                InvocationType="Event",   # async — do NOT wait for result
                Payload=json.dumps(payload).encode("utf-8")
            )
            logger.info(f"Async invoke of {generate_fn} succeeded")
        except Exception as invoke_err:
            logger.error(f"Failed to invoke generate lambda: {invoke_err}")

        # ── Hold Twilio on the line while Gemini works ───────────────────────
        # Pause 35 seconds — long enough for Gemini + Twilio update API call.
        # After the pause, Twilio will hang up gracefully.
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            f'<Say language="{wait_lang}">{wait_msg}</Say>'
            '<Pause length="35"/>'
            '</Response>'
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/xml"},
            "body": twiml
        }

    except Exception as e:
        logger.exception("Error in respond handler")
        return {
            "statusCode": 500,
            "body": str(e)
        }
