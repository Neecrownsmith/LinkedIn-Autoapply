# This file contains information about the candidate's eligibility that will be used in the cover letter and resume.
from datetime import datetime, timedelta
import re

today = datetime.today().date()

def get_notice_days(period):
    period = period.lower().strip()

    if period == "immediate":
        return 0
    
    number = int(re.search(r'\d+', period).group())
    
    if "week" in period:
        return number * 7
    elif "month" in period:
        return number * 30
    elif "day" in period:
        return number
    
    return 0


def next_monday(date):
    days_ahead = (7 - date.weekday()) % 7
    if days_ahead == 0:
        return date
    return date + timedelta(days=days_ahead)



notice_period = "1 month"  # e.g., "2 weeks", "1 month", "Immediate"
notice_days = get_notice_days(notice_period)
after_notice = today + timedelta(days=notice_days)
earliest_start_date = next_monday(after_notice)
available_fulltime = "Yes"  # "Yes", "No"
open_to_contract_or_remote_work = "Yes"  # "Yes", "No"


legally_authorized_to_work = "Yes"  # "Yes", "No", "Decline"
require_visa_sponsorship = "Yes"  # "Yes", "No"
willing_to_relocate = "Yes"  # "Yes", "No"
willing_to_undergo_background_check = "Yes"  # "Yes", "No"
willing_to_travel = "Yes"  # "Yes", "No"
visa_sponsorship = "Yes"  # "Yes", "No"