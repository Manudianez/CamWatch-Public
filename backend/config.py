from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    APP_NAME = "StripWatch"
    VERSION = "0.1.0"

    DEBUG = os.getenv("DEBUG", "False") == "True"