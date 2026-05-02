import os
from google import genai
from google.genai import types
import json
import tempfile


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ):
        # Configuration for Vertex AI
        self.project_id = os.getenv("PROJECT_ID")
        self.location = os.getenv("LOCATION", "us-central1")
        
        # Use the model from .env or default to 2.5 Flash-Lite (the fastest found in your Model Garden)
        self.model = (model or os.getenv("GEMINI_MODEL") or "gemini-2.5-flash-lite").strip()
        self.timeout_seconds = int(timeout_seconds)

        # --- Server/Heroku Authentication Logic ---
        # If GOOGLE_CREDENTIALS env var exists (containing JSON string), write it to a temp file
        google_creds_json = os.getenv("GOOGLE_CREDENTIALS")
        if google_creds_json and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                # Use a temp file for ADC (Application Default Credentials)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode='w') as f:
                    f.write(google_creds_json)
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = f.name
            except Exception as e:
                print(f"Auth Warning: Failed to setup GOOGLE_CREDENTIALS file: {e}")
        # -----------------------------------------------

        # Initialize the client with Vertex AI enabled
        # This will automatically use your gcloud credentials/credits
        self.client = genai.Client(
            vertexai=True, 
            project=self.project_id, 
            location=self.location
        )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
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
                # Clean up potential Markdown formatting if Gemini returns it
                if content.startswith("```json"):
                    content = content.replace("```json", "", 1).rsplit("```", 1)[0].strip()
                elif content.startswith("```"):
                    content = content.replace("```", "", 1).rsplit("```", 1)[0].strip()

                result = json.loads(content)

                if isinstance(result, dict):
                    # Try to extract common keys if it's a nested JSON
                    for key in ("answer", "response", "text", "value"):
                        value = result.get(key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()

                return content

            except json.JSONDecodeError:
                return content

        except Exception as e:
            print(f"Vertex AI Error: {e}")
            return ""

        