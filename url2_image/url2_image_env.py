import os

from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", default="Dg6kPHk8P7G9Zu2JtbgnXe")
JWT_USER = os.getenv("JWT_USER", default="user")
JWT_PASSWORD = os.getenv("JWT_PASSWORD", default="url2image")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", default=False)
USE_LOGIN = bool(int(os.getenv("USE_LOGIN", default=True)))
JWT_ACCESS_TOKEN_EXPIRES = os.getenv("JWT_ACCESS_TOKEN_EXPIRES", default=False)
SELENIUM_WEB_DRIVER_URL = os.getenv("SELENIUM_WEB_DRIVER_URL")
