import os
import json
import argparse
import sys
from datetime import date

def create_profile(profile_name: str):
    profile_dir = os.path.join("profiles", profile_name)
    config_dir = os.path.join(profile_dir, "configuration")

    if os.path.exists(profile_dir):
        print(f"Profile '{profile_name}' already exists at {profile_dir}")
        sys.exit(1)

    os.makedirs(config_dir, exist_ok=True)

    # 1. config.json
    config_data = {
        "_comment": "Add your LinkedIn login credentials below",
        "email": None,
        "password": None
    }
    with open(os.path.join(profile_dir, "config.json"), "w") as f:
        json.dump(config_data, f, indent=4)

    # 2. education.json
    education_data = {
        "_comment_highest_level_of_education": "Options: High School, Associate's Degree, Bachelor's Degree, Master's Degree, Doctorate",
        "highest_level_of_education": None,
        "_comment_degree": "The specific degree obtained",
        "degree": None,
        "_comment_field_of_study": "The field of study for the degree",
        "field_of_study": None,
        "_comment_university": "The name of the university or college attended",
        "university": None,
        "_comment_admission_year": "The year of admission",
        "admission_year": None,
        "_comment_graduation_year": "The year of graduation",
        "graduation_year": None,
        "_comment_gpa": "Grade Point Average (optional)",
        "gpa": None,
        "_comment_relevant_coursework": "A comma-separated list of relevant courses taken (optional)",
        "relevant_coursework": None
    }
    with open(os.path.join(config_dir, "education.json"), "w") as f:
        json.dump(education_data, f, indent=4)

    # 3. personal.json
    personal_data = {
        "first_name": None,
        "middle_name": None,
        "last_name": None,
        "phone_number": None,
        "email_address": None,
        "_comment_preferred_name": "Name used in cover letter/resume",
        "preferred_name": None,
        "_comment_date_of_birth": "Format: YYYY-MM-DD",
        "date_of_birth": None,
        "portfolio_website": None,
        "github_url": None,
        "linkedin_profile_url": None,
        "current_city": None,
        "street": None,
        "state": None,
        "zipcode": None,
        "country": None,
        "_comment_ethnicity": "E.g., Decline, Hispanic/Latino, White, Black or African American, Asian, etc.",
        "ethnicity": None,
        "_comment_gender": "E.g., Male, Female, Other, Decline",
        "gender": None,
        "_comment_disability_status": "E.g., Yes, No, Decline",
        "disability_status": None,
        "_comment_veteran_status": "E.g., Yes, No, Decline",
        "veteran_status": None,
        "languages": None
    }
    with open(os.path.join(config_dir, "personal.json"), "w") as f:
        json.dump(personal_data, f, indent=4)

    # 4. experience.json
    experience_data = {
        "experience": {
            "1": {
                "company_name": None,
                "position": None,
                "duration": None,
                "_comment_description": "List of bullet points for what you did",
                "description": [None, None]
            }
        }
    }
    with open(os.path.join(config_dir, "experience.json"), "w") as f:
        json.dump(experience_data, f, indent=4)

    # 5. skills.json
    skills_data = {
        "_comment_skillset": "Dictionary of skill name mapped to years of experience",
        "skillset": {
            "Python": None,
            "SQL": None
        }
    }
    with open(os.path.join(config_dir, "skills.json"), "w") as f:
        json.dump(skills_data, f, indent=4)

    # 6. salary.json
    salary_data = {
        "_comment_expected_salary": "Your expected salary (e.g. '750 usd/month')",
        "expected_salary": None,
        "_comment_current_salary": "Your current salary",
        "current_salary": None
    }
    with open(os.path.join(config_dir, "salary.json"), "w") as f:
        json.dump(salary_data, f, indent=4)

    # 7. eligibility.json
    eligibility_data = {
        "_comment_today": "Current date",
        "today": str(date.today()),
        "notice_period": None,
        "notice_days": None,
        "after_notice": None,
        "earliest_start_date": None,
        "available_fulltime": None,
        "open_to_contract_or_remote_work": None,
        "legally_authorized_to_work": None,
        "require_visa_sponsorship": None,
        "willing_to_relocate": None,
        "willing_to_undergo_background_check": None,
        "willing_to_travel": None,
        "visa_sponsorship": None
    }
    with open(os.path.join(config_dir, "eligibility.json"), "w") as f:
        json.dump(eligibility_data, f, indent=4)
        
    # 8. job_preferences.json
    job_preferences_data = {
        "keywords": [None],
        "locations": [None],
        "experience_levels": [None],
        "job_types": [None],
        "remote_options": [None],
        "exclude_keywords": [None],
        "max_applications_per_day": None,
        "min_salary": None,
        "max_salary": None,
        "company_blacklist": [],
        "required_skills": [None],
        "preferred_skills": [None]
    }
    with open(os.path.join(profile_dir, "job_preferences.json"), "w") as f:
        json.dump(job_preferences_data, f, indent=4)

    print(f"Successfully created empty profile structure for '{profile_name}' at: {profile_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        create_profile(sys.argv[1])
    else:
        profile_name = input("Enter the username/ID for the new profile: ").strip()
        if profile_name:
            create_profile(profile_name)
        else:
            print("Profile name cannot be empty.")
