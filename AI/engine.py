import os
import json
import re
from typing import Any

from AI.gemini import GeminiClient
from AI.prompt import (
    generate_user_prompt,
    load_information_bank,
    system_prompt,
    generate_resume_user_prompt,
    resume_system_prompt,
)

preferred_llm = os.getenv("PREFERRED_LLM", "gemini").lower()


def answer_job_question(job_description: str, job_question_schema: Any) -> str:
    """High-level helper used by the bot.

    Loads configuration/* as the information bank, builds prompts, calls Gemini,
    and returns a plain-text answer.
    """
    if preferred_llm == "gemini":
        information_bank = load_information_bank()
        user_prompt = generate_user_prompt(job_description, information_bank, job_question_schema)

        client = GeminiClient()
        return client.generate(system_prompt, user_prompt)

    return "{}"


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


def generate_tailored_resume_data(job_description: str) -> dict[str, Any]:
    """Generate structured resume data tailored to a job description."""
    if preferred_llm != "gemini":
        return {}

    information_bank = load_information_bank()
    user_prompt = generate_resume_user_prompt(job_description, information_bank)

    client = GeminiClient()
    raw = client.generate(resume_system_prompt, user_prompt)
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
