import os
import json
import re
from typing import Any
from dotenv import load_dotenv

from AI.gemini import GeminiClient
from AI.groq import GroqClient
from AI.prompt import (
    generate_user_prompt,
    load_information_bank,
    system_prompt,
    generate_resume_user_prompt,
    resume_system_prompt,
    generate_match_user_prompt,
    match_system_prompt,
)


load_dotenv()


def _preferred_llm() -> str:
    return os.getenv("PREFERRED_LLM", "gemini").lower()


def _generate_with_fallback(system_prompt: str, user_prompt: str) -> str:
    preferred = _preferred_llm()
    primary_client = GroqClient() if preferred == "groq" else GeminiClient()
    secondary_client = GeminiClient() if preferred == "groq" else GroqClient()
    primary_name = "Groq" if preferred == "groq" else "Gemini"
    secondary_name = "Gemini" if preferred == "groq" else "Groq"

    # Try primary LLM first
    result = primary_client.generate(system_prompt, user_prompt)
    if result and result.strip():
        return result.strip()

    # If primary failed or hit rate limits, try secondary fallback
    print(f"Primary LLM ({primary_name}) returned empty result or hit rate limit. Trying fallback LLM ({secondary_name})...")
    try:
        fallback_result = secondary_client.generate(system_prompt, user_prompt)
        if fallback_result and fallback_result.strip():
            print(f"Fallback LLM ({secondary_name}) succeeded!")
            return fallback_result.strip()
    except Exception as e:
        print(f"Fallback LLM ({secondary_name}) error: {e}")

    return ""


def answer_job_question(job_description: str, job_question_schema: Any, information_bank: dict = None) -> str:
    """High-level helper used by the bot.

    Loads configuration/* as the information bank, builds prompts, calls LLM,
    and returns a plain-text answer.
    """
    if information_bank is None:
        information_bank = load_information_bank()
    user_prompt = generate_user_prompt(job_description, information_bank, job_question_schema)

    return _generate_with_fallback(system_prompt, user_prompt)


def _extract_json_object(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]
    return raw


def generate_tailored_resume_data(job_description: str, information_bank: dict = None) -> dict[str, Any]:
    """Generate structured resume data tailored to a job description."""
    if information_bank is None:
        information_bank = load_information_bank()
    user_prompt = generate_resume_user_prompt(job_description, information_bank)

    raw = _generate_with_fallback(resume_system_prompt, user_prompt)
    candidate_json = _extract_json_object(raw)

    try:
        parsed = json.loads(candidate_json)
        if isinstance(parsed, dict):
            # Keep source job context so downstream formatting can prioritize relevance.
            parsed["job_description"] = job_description or ""
            return parsed
    except Exception:
        return {}

    return {}


def calculate_match_score(job_description: str, information_bank: dict = None) -> dict[str, Any]:
    """Calculate the match score of a candidate against a job description.

    Returns a dict with:
      - match_score: int
      - verdict: str
      - matched_keywords: list[str]
      - missing_keywords: list[str]
      - summary: str
    """
    if information_bank is None:
        information_bank = load_information_bank()

    user_prompt = generate_match_user_prompt(job_description, information_bank)

    raw = _generate_with_fallback(match_system_prompt, user_prompt)
    candidate_json = _extract_json_object(raw)

    try:
        parsed = json.loads(candidate_json)
        if isinstance(parsed, dict):
            return {
                "match_score": int(parsed.get("match_score", 0)),
                "verdict": str(parsed.get("verdict", "Unknown")),
                "matched_keywords": list(parsed.get("matched_keywords", [])),
                "missing_keywords": list(parsed.get("missing_keywords", [])),
                "summary": str(parsed.get("summary", ""))
            }
    except Exception as e:
        print(f"Failed to parse match score JSON: {e}. Raw output was: {raw}")

    return {
        "match_score": 0,
        "verdict": "Error Parsing",
        "matched_keywords": [],
        "missing_keywords": [],
        "summary": "Failed to calculate match score"
    }

