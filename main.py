from job_bot import LinkedInJobBot
import logging
import random
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import json

def run_for_profile(profile_path: str):
    preferences_file = os.path.join(profile_path, "job_preferences.json")
    job_list = []
    try:
        with open(preferences_file, 'r') as f:
            preferences = json.load(f)
            job_list = [k for k in preferences.get("keywords", []) if k]
    except Exception as e:
        logger.warning(f"Could not load job preferences for {profile_path}: {e}")
        
    if not job_list:
        logger.warning(f"No job keywords found in {preferences_file}. Skipping profile.")
        return
        
    job_title = random.choice(job_list)
    logger.info(f"Using job title: {job_title} for profile {profile_path}")

    bot = LinkedInJobBot(profile_path=profile_path, headless=False)
    if bot.login():
        selected_jobs = []
        if bot.search_jobs(keyword=job_title, time_filter=1800):
            # Apply to up to 5 simple one-click Easy Apply jobs
            selected_jobs = bot.select_jobs()
            logger.info(f"Selected Jobs: {selected_jobs}")

        for job in selected_jobs:  
            submitted = bot.apply_job(job)  # Example job ID, replace with actual ID from search results
            if submitted:
                break

if __name__ == "__main__":
    profiles_dir = "profiles"
    if not os.path.exists(profiles_dir):
        logger.error(f"Profiles directory '{profiles_dir}' not found.")
        exit(1)
        
    for profile_name in os.listdir(profiles_dir):
        profile_path = os.path.join(profiles_dir, profile_name)
        if not os.path.isdir(profile_path):
            continue
            
        logger.info(f"--- Running bot for profile: {profile_name} ---")
        run_for_profile(profile_path)
