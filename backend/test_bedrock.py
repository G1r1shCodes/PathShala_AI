import boto3
import json

def test_bedrock():
    try:
        client = boto3.client("bedrock-runtime", region_name="ap-south-1")
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "Hi"}],
        })
        response = client.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        print("Success!")
        print(json.loads(response["body"].read()))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bedrock()
