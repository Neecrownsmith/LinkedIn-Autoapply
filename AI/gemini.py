import os
from google import genai
from google.genai import types
import json


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        self.model = (model or os.getenv("GEMINI_MODEL") or "gemini-1.5-flash").strip()
        self.timeout_seconds = int(timeout_seconds)

        if not self.api_key:
            raise ValueError(
                "Missing Gemini API key. Set GEMINI_API_KEY (or GOOGLE_API_KEY) in your environment."
            )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = genai.Client(api_key=self.api_key)

        response = client.models.generate_content(
            model=self.model,
            contents=[
                system_prompt,
                user_prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )

        content = (response.text or "").strip()

        if not content:
            return ""

        try:
            result = json.loads(content)

            if isinstance(result, dict):
                for key in ("answer", "response", "text", "value"):
                    value = result.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()

            return content

        except json.JSONDecodeError:
            return content

        