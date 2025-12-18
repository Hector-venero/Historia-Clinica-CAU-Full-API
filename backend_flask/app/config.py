# backend_flask/app/config.py
import os
from datetime import timedelta

class Config:
    # 🔒 Seguridad general
    SECRET_KEY = os.getenv("SECRET_KEY", "CambiaEstoPorUnValorSeguro")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = True

    # 📧 Configuración de correo (ahora desde entorno)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    # 💾 Base de datos (ya no usar root)
    DB_CONFIG = {
        "host": os.getenv("DB_HOST", "db"),
        "user": os.getenv("DB_USER", "hc_app"),
        "password": os.getenv("DB_PASSWORD", "hc_password"),
        "database": os.getenv("DB_NAME", "hc_bfa"),
    }
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/app/uploads")
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # Limite de 20MB también en Flask (por seguridad)