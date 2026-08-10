import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PREFIX = "!"

OWNER_IDS = [
    # tu id si quieres
]