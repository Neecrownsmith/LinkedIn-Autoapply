# LinkedIn Auto-Apply Bot

Python automation project for LinkedIn Easy Apply with AI-assisted form answering and tailored resume generation.

## What This Project Does

- Logs into LinkedIn with cookie reuse and checkpoint handling.
- Searches jobs using URL filters (keywords, location scope, remote/onsite, Easy Apply, time range).
- Prioritizes job cards by signals like top applicant and actively reviewing.
- Opens Easy Apply, inspects form fields, and builds a schema of required inputs.
- Uses Gemini to generate JSON answers for form questions.
- Optionally generates a tailored resume from your configuration data and job description.
- Uploads the generated resume into file inputs.
- Moves through Easy Apply steps, clicks Review, then clicks Submit application.

## Current Project Structure

```text
.
├── main.py
├── job_bot.py
├── job_preferences.json
├── requirements.txt
├── .env
├── linkedin_cookies.json
├── AI/
│   ├── engine.py
│   ├── gemini.py
│   ├── prompt.py
│   └── resume_pdf.py
├── configuration/
│   ├── personal.py
│   ├── experience.py
│   ├── education.py
│   ├── skills.py
│   ├── salary.py
│   ├── eligibility.py
│   └── feedback.txt
└── resume/
    └── generated_resumes/
```

## Requirements

- Python 3.10+
- Google Chrome installed
- LinkedIn account
- Gemini API key (if using AI features)

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Install Playwright Chromium (used for high-fidelity HTML to PDF rendering):

```bash
python -m playwright install chromium
```

## Environment Variables

Create or update `.env` with:

```env
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

# AI
GEMINI_API_KEY=your_gemini_api_key
# or GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-1.5-flash
PREFERRED_LLM=gemini

# Resume tailoring toggle
TAILOR_RESUME=yes

# Optional
CHROME_VERSION=
```

Notes:
- `TAILOR_RESUME=yes` enables tailored resume generation and upload.
- If Gemini key is missing and AI paths are used, generation will fail.

## Configuration Data

All candidate data used by the AI is loaded from `configuration/*.py`.

Update these files before running:
- `configuration/personal.py`
- `configuration/experience.py`
- `configuration/education.py`
- `configuration/skills.py`
- `configuration/salary.py`
- `configuration/eligibility.py`

## Run

```bash
python main.py
```

Current `main.py` flow:
1. Initialize `LinkedInJobBot`.
2. Login.
3. Search jobs with `job_title`.
4. Select prioritized jobs.
5. Apply to the first selected job via Easy Apply flow.

## Easy Apply Flow Summary

In `job_bot.py`, the application path is:
1. Open selected job and extract job description.
2. Click Easy Apply.
3. Extract form schema (`get_form_questions`).
4. Generate tailored resume JSON (optional).
5. Render PDF resume (`AI/resume_pdf.py`) and upload to file inputs.
6. Generate LLM answers for form fields.
7. Fill fields, click Next through steps, click Review.
8. Click Submit application.

## PDF Rendering

Resume PDF generation uses this fallback order:
1. Playwright Chromium render (best HTML/CSS fidelity)
2. `xhtml2pdf`
3. Minimal internal PDF writer (last-resort fallback)

Generated files are saved under `resume/generated_resumes/`.

## Safety and Responsibility

Use responsibly and at your own risk.

- Respect LinkedIn Terms of Service.
- Keep request frequency low.
- Prefer manual monitoring while running automation.
- Avoid spam or abusive behavior.

## Troubleshooting

- Login/checkpoint loops:
  - Delete `linkedin_cookies.json` and login again.
- No jobs selected:
  - Broaden keyword/time filters.
- Resume styling mismatch:
  - Ensure Playwright Chromium is installed.
- Gemini errors:
  - Verify `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
- File upload not detected:
  - Keep `TAILOR_RESUME=yes` and verify PDF path generation in logs.

## Disclaimer

This repository is for educational/personal automation experiments. You are responsible for compliance with platform rules and local laws.
