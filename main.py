from job_bot import LinkedInJobBot
import logging


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

job_title = "Software Engineer"



bot = LinkedInJobBot(headless=True)
if bot.login():

    # Example: Python developer in UK (any work type, easy apply only)
    if bot.search_jobs(keyword=job_title, time_filter=1800):
        # Apply to up to 5 simple one-click Easy Apply jobs
        selected_jobs = bot.select_jobs()
        logger.info(f"Selected Jobs: {selected_jobs}")

    for job in selected_jobs:  
        submitted = bot.apply_job(job)  # Example job ID, replace with actual ID from search results
        if submitted:
            break

    # print(f"Job Description: {job_description}")
