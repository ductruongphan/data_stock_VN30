from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

# Tải biến môi trường từ tệp .env
load_dotenv()

class Config:
    MONGO_USER = os.getenv("MONGO_USER")
    MONGO_PASS = os.getenv("MONGO_PASS")
    MONGO_CLUSTER = os.getenv("MONGO_CLUSTER")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

    # Mã hóa tên người dùng và mật khẩu
    MONGO_USER_ESCAPED = quote_plus(MONGO_USER)
    MONGO_PASS_ESCAPED = quote_plus(MONGO_PASS)

    MONGO_URI = f"mongodb+srv://{MONGO_USER_ESCAPED}:{MONGO_PASS_ESCAPED}@{MONGO_CLUSTER}/{MONGO_DB_NAME}?retryWrites=true&w=majority"

    DEBUG = os.getenv("DEBUG", True)
    SECRET_KEY = os.getenv("SECRET_KEY")
    WTF_CSRF_ENABLED = True
