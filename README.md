# LinkedIn Auto-Apply Bot

An intelligent, multi-profile LinkedIn automation bot for searching jobs, calculating compatibility match scores, dynamically tailoring resume experiences, and applying via Easy Apply. Supports both **Google Gemini** and **Groq** AI backends.

---

## 🚀 Key Features

* **Multi-Profile Support**: Manage independent credentials, cookies, job preferences, and resume data for multiple candidates under the `profiles/` directory.
* **Dual AI Orchestration**: Seamlessly toggle between Google Gemini (using the Google GenAI SDK) and Groq (using high-speed direct REST API calls).
* **AI Match Scorer**: Dynamically evaluates compatibility (0–100 score, fit summary, and verdict) against target roles before applying.
* **On-the-Fly Resume Tailoring**: Automatically drafts resume experience bullet points matching ATS keywords using the Google XYZ formula and renders them into a professional PDF.
* **13-Column Activity Tracker**: Logs evaluations, custom resume text, and form answers directly to a Google Sheet (with auto-fallback to local `job_tracker.csv`).
* **API Spikes Resiliency**: Built-in exponential backoff retries to handle rate limits (429) and demand spikes (503) seamlessly.
* **Zero Local Storage Growth**: Safely cleans up temporary local PDF files post-application.

---

## 📁 Project Structure

```text
.
├── main.py                    # Multi-profile check loop (runs run_for_profile)
├── job_bot.py                 # Core Selenium automation bot
├── service_account.json       # Google Sheets service account credentials
├── requirements.txt           # Package dependencies
├── .env                       # Environment credentials and configurations
├── AI/
│   ├── engine.py              # AI orchestrator (hot-swaps LLM clients)
│   ├── gemini.py              # Gemini client with retry backoff logic
│   ├── groq.py                # Groq client with retry backoff logic
│   ├── prompt.py              # System & User prompts for scoring & resume tailoring
│   └── resume_pdf.py          # High-fidelity Playwright/xhtml2pdf resume renderer
└── profiles/                  # Candidate folders
    ├── adeniyi/
    │   ├── linkedin_cookies.json  # Saved session cookies (avoids log-in alerts)
    │   ├── job_preferences.json   # Targeted keywords and locations
    │   ├── job_tracker.csv        # Local backup activity logs (13 columns)
    │   ├── config.json            # Profile specific email/password overrides
    │   └── configuration/         # Profile candidate JSON files for AI
    │       ├── personal.json
    │       ├── experience.json
    │       ├── education.json
    │       └── skills.json
    └── bayo/
```

---

## 🛠️ Requirements & Setup

### Prerequisites
* Python 3.10+
* Google Chrome installed

### 1. Installation
Install the project dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)
Create a `.env` file in the root directory:
```env
# LinkedIn Credentials
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

# LLM Selection ("gemini" or "groq")
PREFERRED_LLM=groq

# Gemini Configuration (If using gemini)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash-lite
GEMINI_MODE=standard

# Groq Configuration (If using groq)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# Job Selection Gating
MATCH_THRESHOLD=75
TAILOR_RESUME=true

# Activity Logging
GOOGLE_SHEET_ID=your_google_sheet_id_here
CHROME_VERSION=145.0.7632.117
```

### 3. Google Sheets Integration
* Place your Google Cloud service account key as `service_account.json` in the root folder.
* Share your target Google Sheet (using the `GOOGLE_SHEET_ID` from `.env`) with the service account client email as an **Editor**.
* The bot will automatically check and upgrade your sheet to the 13-column layout on the first run.

---

## 📋 Spreadsheet Tracking Columns
Both the Google Sheet and the local `job_tracker.csv` maintain the exact same structured data columns:
1. **Date**: Timestamp of the evaluation.
2. **Profile**: The candidate folder name (e.g. `adeniyi` or `bayo`).
3. **Job ID**: LinkedIn Job Identifier.
4. **Job Title**: The scraped role title.
5. **Company**: Hiring organization.
6. **Location**: Scraped role location.
7. **Match Score**: Evaluated compatibility score (0-100).
8. **Verdict**: Verdict description (`Strong Fit`, `Good Fit`, `Fair Fit`, `Weak Fit`).
9. **AI Verdict Summary**: Explanatory text detailing fits and experience gaps.
10. **Status**: Action state (`Applied`, `Skipped - Low Match`, `Skipped - Form Incomplete`).
11. **Form Answers**: JSON dump of custom question responses filled by AI.
12. **Tailored CV Content**: Shareable Google Drive link, or the raw formatted tailored resume text block if the service account runs into Drive storage quota constraints.
13. **Job URL**: Link to the role on LinkedIn.

---

## 🚀 Running the Bot

Run the multi-profile loop:
```bash
python main.py
```

### Automation Flow:
1. Loops through all subfolders in the `profiles/` directory.
2. Reads the profile's targeted job keywords and selects one at random.
3. Launches a Selenium Chrome instance (reusing cookies to skip checkpoints).
4. Searches for matching jobs posted within the last 30 minutes.
5. For each job card:
   - Scrapes the description and queries the chosen LLM (`PREFERRED_LLM`) for a match score.
   - If the score is below the `MATCH_THRESHOLD`, it skips the job and logs the skip.
   - If the score is high, it clicks **Easy Apply**, generates/formats a tailored resume PDF, uploads it, answers form questions using AI profile details, and submits the application.
   - Once **one** job is successfully submitted per candidate profile, the loop breaks and moves to the next candidate profile to preserve rate safety.
