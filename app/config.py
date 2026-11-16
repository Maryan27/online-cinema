import os
from pathlib import Path

MEDIA_DIR = Path("media")
AD_VIDEO_URL = "/media/videos/ad.mp4"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cinema.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

FRONTEND_DIR = Path("frontend")