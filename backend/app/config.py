"""App settings, loaded from environment variables / .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (SQLite for dev; swap to Postgres URL for the demo if you like)
    database_url: str = "sqlite:///./callbell.db"

    # "bedrock" (real) or "mock" (offline keyword classifier for dev only)
    llm_provider: str = "bedrock"

    # AWS Bedrock
    aws_region: str = "us-east-1"
    # Verify the exact model ID / inference profile enabled in YOUR Bedrock console.
    bedrock_model_id: str = "us.amazon.nova-lite-v1:0"
    llm_timeout_seconds: float = 5.0
    llm_min_confidence: float = 0.7

    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_stt_model: str = "scribe_v1"        # verify current model id in ElevenLabs docs
    elevenlabs_tts_voice_id: str = ""              # pick a voice in the ElevenLabs dashboard
    elevenlabs_tts_model: str = "eleven_multilingual_v2"
    enable_tts: bool = False                       # P1 feature: speak confirmations back

    # CORS for the React dev server
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
