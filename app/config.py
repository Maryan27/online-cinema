import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cinema.db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
