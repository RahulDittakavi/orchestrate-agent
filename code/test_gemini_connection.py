"""
test_gemini_connection.py — Verify GEMINI_API_KEY is valid and Gemini is reachable.

Usage:
    python code/test_gemini_connection.py
"""

import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

GEMINI_MODEL = "gemini-2.5-flash"

def test_connection():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[✗] GEMINI_API_KEY is not set. Add it to code/.env")
        sys.exit(1)

    print(f"[→] API key found: {api_key[:8]}...{api_key[-4:]}")
    print(f"[→] Connecting to {GEMINI_MODEL}...")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents="Reply with exactly one word: CONNECTED",
        config=types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=20,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )

    text = (response.text or "").strip()
    print(f"[✓] Gemini responded: {text!r}")
    print("[✓] Connection test PASSED")

if __name__ == "__main__":
    try:
        test_connection()
    except Exception as e:
        print(f"[✗] Connection test FAILED: {e}")
        sys.exit(1)
