import requests
import json
import logging

url = "https://pathshala-ai.onrender.com/generate-lesson"
payload = {
    "transcript": "आज मुझे कक्षा 1 को स्वर सिखाने हैं",
    "whatsapp_number": "+916369631956"
}
headers = {
    "Content-Type": "application/json"
}

try:
    print("Sending request to:", url)
    print("Payload:", payload)
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    print("Status Code:", response.status_code)
    try:
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print("Raw Output:", response.text)
except Exception as e:
    print("Error:", e)
