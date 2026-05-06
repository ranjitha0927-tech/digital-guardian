import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    INSTANCE_DIR = BASE_DIR / "instance"
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_SECONDS", str(60 * 60 * 12)))
    DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").strip().lower()
    SQLITE_PATH_RAW = os.getenv(
        "SQLITE_PATH",
        str(INSTANCE_DIR / "digital_guardian.db"),
    )
    SQLITE_PATH = Path(SQLITE_PATH_RAW)
    if not SQLITE_PATH.is_absolute():
        SQLITE_PATH = BASE_DIR / SQLITE_PATH
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DB_ENGINE == "mysql":
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}"
            f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'digital_guardian')}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{SQLITE_PATH.as_posix()}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").strip().lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").strip().lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip() or None
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "").strip() or None
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "alerts@digitalguardian.local")

    ML_BASE_DIR = Path(os.getenv("ML_BASE_DIR", str(BASE_DIR / "ml")))
    ML_DATA_DIR = ML_BASE_DIR / "data"
    ML_ARTIFACT_DIR = Path(os.getenv("ML_ARTIFACT_DIR", str(INSTANCE_DIR / "ml_artifacts")))
    ML_MODEL_PATH = ML_ARTIFACT_DIR / "hybrid_text_classifier.pkl"
    ML_METADATA_PATH = ML_ARTIFACT_DIR / "hybrid_text_classifier_metadata.json"
    ML_AUTO_TRAIN = os.getenv("ML_AUTO_TRAIN", "true").strip().lower() == "true"
