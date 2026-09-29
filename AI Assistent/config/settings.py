"""
Configuration settings for Selvie Personal AI Assistant.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "backend" / "database" / "selvie.db"

class Settings(BaseSettings):
    USER_NAME: str = "Saksham"
    ASSISTANT_NAME: str = "Selvie"
    PORT: int = 8765
    HOST: str = "127.0.0.1"

    # AI Brain
    LLM_PROVIDER: str = "ollama"  # ollama | cloud | rules
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    CLOUD_API_KEY: str = ""
    CLOUD_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    CLOUD_MODEL: str = "gemini-1.5-flash"

    # Voice / Speech
    # Default to high-quality Indian female voice
    TTS_VOICE: str = "en-IN-NeerjaExpressiveNeural"
    TTS_VOICE_FALLBACK: str = "en-IN-NeerjaNeural"
    TTS_HINDI_VOICE: str = "hi-IN-SwaraNeural"
    TTS_RATE: str = "+0%"
    TTS_PITCH: str = "+0Hz"

    # Global Hotkey & Windows Behavior
    GLOBAL_HOTKEY: str = "Ctrl+Space"
    AUTO_START_WINDOWS: bool = True
    QUIET_MODE: bool = False
    CONFIRMATION_REQUIRED: bool = True

    # Paths
    BASE_DIR: Path = BASE_DIR
    DB_PATH: Path = DB_PATH
    ASSETS_DIR: Path = BASE_DIR / "assets"
    FRONTEND_DIR: Path = BASE_DIR / "frontend"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
