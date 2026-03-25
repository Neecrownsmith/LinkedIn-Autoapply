

import json
import importlib
import pkgutil
import types
from typing import Any


system_prompt = """You are an assistant helping complete job applications.

Rules:
- Return ONLY valid JSON. No markdown, no code fences, no commentary.
- The top-level JSON must be an object whose keys exactly match the question labels from QUESTION SCHEMA.
- Each value should usually be a single string answer.
- For checkbox questions that may need multiple selections, the value may be an array of strings.
- If a question is about marking the job as a top choice (for example: "Mark this job as top choice"), return [] for that key.
- If the question expects Yes/No, answer with exactly "Yes" or "No".
- If the UI provides acceptable values/options, choose from those values exactly.
- Keep answers short and application-friendly.
- Use the provided information bank; do not invent credentials or experience.
"""


def load_information_bank() -> dict[str, Any]:
    """Load candidate data from configuration/*.py into a JSON-serializable dict.

    This is future-proof: any new public variables you add to files under
    configuration/ automatically appear in the information bank.

    Structure:
      {
        "personal": { ...all public vars from configuration/personal.py... },
        "education": { ... },
        ...
      }
    """

    def to_jsonable(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        # Common containers
        if isinstance(value, (list, tuple, set)):
            return [to_jsonable(v) for v in value]
        if isinstance(value, dict):
            out: dict[str, Any] = {}
            for k, v in value.items():
                out[str(k)] = to_jsonable(v)
            return out

        # Avoid embedding code objects / modules / classes
        if callable(value) or isinstance(value, (types.ModuleType, type)):
            return None

        # Dates / datetimes and other objects: stringify
        try:
            return str(value)
        except Exception:
            return None

    info: dict[str, Any] = {}

    try:
        configuration_pkg = importlib.import_module("configuration")
    except Exception:
        return info

    pkg_paths = getattr(configuration_pkg, "__path__", None)
    if not pkg_paths:
        return info

    for module_info in pkgutil.iter_modules(pkg_paths):
        mod_name = module_info.name
        if mod_name.startswith("_"):
            continue
        if mod_name == "__pycache__":
            continue

        fqmn = f"configuration.{mod_name}"
        try:
            mod = importlib.import_module(fqmn)
        except Exception:
            info[mod_name] = {}
            continue

        data: dict[str, Any] = {}
        for k, v in vars(mod).items():
            if k.startswith("_"):
                continue
            if callable(v) or isinstance(v, (types.ModuleType, type)):
                continue
            jsonable = to_jsonable(v)
            if jsonable is None:
                continue
            data[k] = jsonable

        info[mod_name] = data

    return info


def generate_user_prompt(
    job_description: str, 
    information_bank: dict[str, Any], 
    job_question_schema: Any) -> str:

    bank_json = json.dumps(information_bank or {}, indent=2, ensure_ascii=False)
    schema_json = json.dumps(job_question_schema or {}, indent=2, ensure_ascii=False)

    return (
        "You are helping answer job application questions.\n\n"
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"QUESTION SCHEMA:\n{schema_json}\n\n"
        "INFORMATION BANK (JSON):\n"
        f"{bank_json}\n\n"
        "Based on the above, produce a JSON object containing answers for every question in QUESTION SCHEMA. "
        "The keys in the JSON must exactly match the question labels from QUESTION SCHEMA. "
        "Each value must be a string, except checkbox answers may be an array of strings. "
        "If a key is about marking the job as top choice, set that key to []."
    )



resume_system_prompt = """You are an assistant generating tailored resume content for a job application.

Rules:
- Return ONLY valid JSON. No markdown, no code fences, no commentary.
- Use only information present in INFORMATION BANK and JOB DESCRIPTION context.
- Do not invent employers, dates, certifications, degrees, or skills.
- Keep wording concise and ATS-friendly.
- Focus on relevance to the target role.
- `headline` must be role-only text (not a sentence), e.g. "Python Backend Developer | Data Scientist".
- Do not include years of experience, verbs, or descriptive clauses in `headline`.
- Headline and all other fields should be tailored to the job description, emphasizing the most relevant skills and experience from the information bank.


Output schema:
{
    "full_name": "string",
    "headline": "string",
    "summary": "string",
    "skills": ["string"],
    "experience": [
        {
            "title": "string",
            "company": "string",
            "start": "string",
            "end": "string",
            "bullets": ["string"]
        }
    ],
    "education": [{
        "school": "string",
        "degree": "string",
        "start": "string",
        "end": "string"
    }
    ],
    "projects": [{
        "name": "string",
        "description_bullets": ["string"]
    }
    ]
"""


def generate_resume_user_prompt(job_description: str, information_bank: dict[str, Any]) -> str:
        bank_json = json.dumps(information_bank or {}, indent=2, ensure_ascii=False)

        return (
                "You are preparing a tailored resume for this job.\n\n"
                f"JOB DESCRIPTION:\n{job_description}\n\n"
                "INFORMATION BANK (JSON):\n"
                f"{bank_json}\n\n"
            "Return resume JSON that follows the schema from the system prompt. "
            "For headline, output role labels only (e.g., 'Python Backend Developer | Data Scientist')."
        )