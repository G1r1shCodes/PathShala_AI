import logging
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for the initial Twilio /call-webhook
    """
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response>'
        '<Gather input="speech" action="/call-webhook/respond" timeout="3" speechTimeout="auto" language="hi-IN">'
        '<Say language="hi-IN">Namaste! Aaj ka lesson request boliye. Jaise — Class 3 multiplication, ya Class 5 plants.</Say>'
        '</Gather>'
        '</Response>'
    )
    
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/xml"},
        "body": twiml
    }
