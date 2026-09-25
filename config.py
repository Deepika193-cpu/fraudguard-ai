import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    APP_NAME = "FraudGuard AI"
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-change-this-secret-key")

    DATABASE = os.getenv(
        "DATABASE_PATH",
        str(BASE_DIR / "instance" / "fraud_detection.db"),
    )
    ML_MODEL_PATH = os.getenv(
        "ML_MODEL_PATH",
        str(BASE_DIR / "model_artifacts" / "best_fraud_detection_model.pkl"),
    )
    RL_MODEL_PATH = os.getenv(
        "RL_MODEL_PATH",
        str(BASE_DIR / "model_artifacts" / "fraud_q_learning_policy.pkl"),
    )

    TRANSACTION_TYPES = ("CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER")
    LOGS_PER_PAGE = 12
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    WTF_CSRF_TIME_LIMIT = 3600
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024
