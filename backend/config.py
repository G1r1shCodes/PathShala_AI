"""
config.py — Environment variable configuration for PathShala AI backend.
All secrets and service settings loaded from environment / .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AWS Bedrock
    AWS_REGION: str = "ap-south-1"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # AWS credentials — set these in environment or .env
    # boto3 will also pick them up from ~/.aws/credentials automatically
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # Twilio — WhatsApp delivery
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "+14155238886"   # Twilio Sandbox default
    TWILIO_WHATSAPP_TO: str = ""                 # Your test number (fallback if not passed per-request)

    # App
    APP_ENV: str = "development"
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
