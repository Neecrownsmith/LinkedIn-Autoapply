import os
import json
import requests
import time
from dotenv import load_dotenv

load_dotenv()

class GroqClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ):
        self.api_key = (api_key or os.getenv("GROQ_API_KEY") or "").strip()
        self.model = (model or os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile").strip()
        self.timeout_seconds = int(timeout_seconds)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call the Groq API to generate chat completions with exponential backoff retries."""
        if not self.api_key:
            print("Groq Client Warning: GROQ_API_KEY is not defined in .env")
            return ""

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"}
        }

        max_retries = 3
        backoff_factor = 2.0

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds
                )
                
                # Check for transient rate limits or server overloads (429 or 5xx)
                if response.status_code in {429, 502, 503, 504}:
                    if attempt < max_retries - 1:
                        sleep_time = (backoff_factor ** attempt) + 1.0
                        print(f"Groq API status {response.status_code}. Retrying in {sleep_time}s (Attempt {attempt+1}/{max_retries})...")
                        time.sleep(sleep_time)
                        continue
                
                response.raise_for_status()
                data = response.json()
                
                choices = data.get("choices", [])
                if not choices:
                    return ""
                    
                content = (choices[0].get("message", {}).get("content", "")).strip()
                
                # Clean up markdown formatting if returned
                if content.startswith("```json"):
                    content = content.replace("```json", "", 1).rsplit("```", 1)[0].strip()
                elif content.startswith("```"):
                    content = content.replace("```", "", 1).rsplit("```", 1)[0].strip()
                    
                try:
                    result = json.loads(content)
                    if isinstance(result, dict):
                        # Try to extract common keys if nested
                        for key in ("answer", "response", "text", "value"):
                            value = result.get(key)
                            if isinstance(value, str) and value.strip():
                                return value.strip()
                    return content
                except json.JSONDecodeError:
                    return content

            except Exception as e:
                err_msg = str(e).lower()
                is_transient = "429" in err_msg or "503" in err_msg or "timeout" in err_msg or "connection" in err_msg
                
                if is_transient and attempt < max_retries - 1:
                    sleep_time = (backoff_factor ** attempt) + 1.0
                    print(f"Groq API connection error: {e}. Retrying in {sleep_time}s (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(sleep_time)
                else:
                    print(f"Groq API Final Error: {e}")
                    return ""
                    
        return ""
