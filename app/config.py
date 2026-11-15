import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

class Settings(BaseSettings):
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    # Optional: restricted to single user chat_id for privacy, if empty anyone can talk
    ALLOWED_TELEGRAM_USER_ID: str = ""

    # Google Gemini API
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # User Profile (21 y/o male, 168cm, 89kg -> 70kg)
    USER_NAME: str = "Champion"
    USER_AGE: int = 21
    USER_GENDER: str = "male"
    USER_HEIGHT_CM: float = 168.0
    USER_CURRENT_WEIGHT_KG: float = 89.0
    USER_TARGET_WEIGHT_KG: float = 70.0
    
    # Calorie Budget & Targets
    # BMR = (10 * 89) + (6.25 * 168) - (5 * 21) + 5 = 1,840 kcal
    # Sedentary Maintenance = 1,840 * 1.2 = ~2,208 kcal
    # Daily Deficit Target = -500 kcal -> ~1,700 kcal
    DAILY_CALORIE_BUDGET: int = 1750
    DAILY_PROTEIN_TARGET_G: int = 120
    DAILY_WATER_TARGET_LITERS: float = 3.5

    # App & Web Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'caloriebot.db'}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
