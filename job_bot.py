import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import logging
import time
import random
import pickle
import json
from typing import Any
from dotenv import load_dotenv
from urllib.parse import urlencode, quote_plus
from AI.engine import answer_job_question, generate_tailored_resume_data
from AI.resume_pdf import render_resume_pdf
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


tailor_resume = os.getenv("TAILOR_RESUME", "no").lower() in ["true","yes"]


class LinkedInJobBot:
    """LinkedIn Job Application Automation Bot with Local ChromeDriver"""
    
    def __init__(self, headless: bool = False):
        """
        Initialize LinkedIn Job Bot
        
        Args:
            headless: Run browser in headless mode
            chromedriver_path: Path to ChromeDriver executable
        """
        self.url = "https://www.linkedin.com/"
        self.jobs_url = "https://www.linkedin.com/jobs/"
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        self.driver = None
        self.headless = headless
        self.cookies_file = "linkedin_cookies.json"
        self.chrome_version = os.getenv('CHROME_VERSION')  # Read from .env
        self.wait = None  # Will be set after driver is initialized


    def setup_driver(self):
        """Setup Chrome driver using Selenium's built-in driver manager.

        This avoids ChromeDriverManager-related WinError 193 issues on Windows
        by letting Selenium download and manage the matching ChromeDriver
        binary automatically.
        """
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-background-networking')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-notifications')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-gcm')
            options.add_argument('--remote-debugging-port=0')
            options.add_argument('--log-level=3')

            # User agent
            user_agent = getattr(self, 'user_agent', None) or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            options.add_argument(f'--user-agent={user_agent}')

            if self.headless:
                options.add_argument('--headless=new')

            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("detach", True)

            try:
                # Prefer Selenium Manager (built into Selenium 4.6+)
                # It will auto-download the correct ChromeDriver.
                logger.info("Setting up ChromeDriver via Selenium Manager (no ChromeDriverManager).")
                service = Service()  # Let Selenium determine the driver binary
                self.driver = webdriver.Chrome(service=service, options=options)

            except Exception as driver_error:
                # Fallback: try to use system Chrome driver (chromedriver in PATH)
                logger.warning(f"Selenium Manager failed to start ChromeDriver: {driver_error}")
                logger.info("Attempting to use system-installed ChromeDriver from PATH...")

                try:
                    self.driver = webdriver.Chrome(options=options)
                except Exception as path_error:
                    logger.error(f"System ChromeDriver also failed: {path_error}")
                    raise Exception("Could not initialize ChromeDriver with any method")
                    

            # Anti-detection JS tweaks
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")

            # Set up WebDriverWait now that driver is initialized
            self.wait = WebDriverWait(self.driver, 10)

            logger.info("Chrome driver setup successful")
            return True
        except Exception as e:
            logger.error(f"Failed to setup driver: {str(e)}")
            return False
    
    def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def type_like_human(self, element, text: str):
        """Type text with human-like delays between keystrokes"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

    def redirect(self, redirection_url= "login"):
        if redirection_url.startswith("/"):
            redirection_url = redirection_url.lstrip("/")

        redirection = f"{self.url}/{redirection_url}"
        return redirection

    def save_cookies(self):
        """Save current session cookies to file"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
            logger.info(f"Cookies saved to {self.cookies_file}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {str(e)}")

    def load_cookies(self):
        """Load cookies from file and add to driver"""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                
                # Navigate to LinkedIn first to set cookies
                self.driver.get(self.url)
                self.random_delay(2, 3)
                
                # Add cookies to driver, track whether key auth cookies were added
                auth_cookie_names = {"li_at", "JSESSIONID"}
                added_auth_cookies = set()

                for cookie in cookies:
                    name = cookie.get('name', 'unknown')
                    try:
                        self.driver.add_cookie(cookie)
                        if name in auth_cookie_names:
                            added_auth_cookies.add(name)
                    except Exception as cookie_error:
                        logger.warning(f"Failed to add cookie {name}: {str(cookie_error)}")
                
                if not added_auth_cookies:
                    logger.info("Auth cookies could not be loaded; will require manual login")
                    return False

                logger.info("Cookies loaded successfully (auth cookies present)")
                return True
            else:
                logger.info("No cookie file found")
                return False
        except Exception as e:
            logger.error(f"Failed to load cookies: {str(e)}")
            return False

    def is_logged_in(self):
        """Check if user is already logged in"""
        try:
            # Navigate to feed page to check if logged in
            self.driver.get(f"{self.url}feed/")
            self.random_delay(3, 5)
            
            current_url = self.driver.current_url.lower()
            page_source = self.driver.page_source.lower()

            # If we got bounced to a checkpoint page, wait for user to finish 2FA
            if "checkpoint" in current_url:
                logger.info("Detected LinkedIn checkpoint; waiting for user to complete verification...")
                if not self.wait_for_checkpoint_resolution():
                    logger.info("Checkpoint not resolved in time; not logged in")
                    return False

                # Re-read URL and page source after checkpoint resolution
                self.random_delay(2, 4)
                current_url = self.driver.current_url.lower()
                page_source = self.driver.page_source.lower()

            # If we are on a login page, clearly not logged in
            if "login" in current_url:
                logger.info("Detected LinkedIn login page; not logged in")
                return False

            # Heuristic: look for signs of the signed-in feed UI
            if "feed" in current_url or "mynetwork" in current_url:
                if "global-nav" in page_source or "me-wvmp-link" in page_source:
                    logger.info("Already logged in via cookies")
                    return True

            logger.info("Not logged in, cookies may be expired or invalid")
            return False
        except Exception as e:
            logger.error(f"Error checking login status: {str(e)}")
            return False

    def wait_for_checkpoint_resolution(self, timeout_seconds: int = 300) -> bool:
        """Wait while the LinkedIn checkpoint/2FA page is displayed.

        This allows the user to approve the login on their phone and
        then automatically continues once LinkedIn redirects away from
        the checkpoint URL.
        """
        start_time = time.time()
        logger.info("Please approve the LinkedIn login on your phone or device.")

        while time.time() - start_time < timeout_seconds:
            current_url = self.driver.current_url.lower()

            # Once we're no longer on a checkpoint URL, consider it resolved
            if "checkpoint" not in current_url:
                logger.info("Checkpoint challenge appears resolved.")
                return True

            # Small sleep to avoid hammering the browser
            time.sleep(5)

        logger.error("Timed out waiting for LinkedIn checkpoint/2FA to be resolved.")
        return False

    def login(self):
        try:
            if not self.driver:
                if not self.setup_driver():
                    return False
            
            # Try to use existing cookies first
            logger.info("Attempting to login using saved cookies...")
            if self.load_cookies():
                if self.is_logged_in():
                    logger.info("Successfully logged in using cookies!")
                    return True
                else:
                    logger.info("Cookies expired or invalid, proceeding with manual login")
            
            # Manual login process
            logger.info("Performing manual login...")
            login_url = self.redirect("login")
            self.driver.get(login_url)
            self.random_delay(4, 7)

            
            
            # Find and fill email field
            email_field = self.wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="username"]')))
            self.type_like_human(email_field, self.email)
            self.random_delay(1, 2)
            
            # Find and fill password field
            password_field = self.wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="password"]')))
            self.type_like_human(password_field, self.password)
            self.random_delay(1, 2)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            self.random_delay(3, 5)
            
            # Handle potential checkpoint/2FA after manual login
            current_url = self.driver.current_url.lower()
            if "checkpoint" in current_url:
                logger.info("Checkpoint detected after manual login; waiting for verification...")
                if not self.wait_for_checkpoint_resolution():
                    logger.error("Checkpoint was not resolved; login failed")
                    return False
                self.random_delay(2, 4)
                current_url = self.driver.current_url.lower()

            if "feed" in current_url or "mynetwork" in current_url:
                logger.info("Manual login successful!")
                # Save cookies for future use
                self.save_cookies()
                return True
            else:
                logger.error("Login failed - redirected to unexpected page")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False

    def clear_cookies(self):
        """Clear saved cookies file and browser cookies"""
        try:
            # Remove cookies file
            if os.path.exists(self.cookies_file):
                os.remove(self.cookies_file)
                logger.info(f"Cookies file {self.cookies_file} removed")
            
            # Clear browser cookies if driver is active
            if self.driver:
                self.driver.delete_all_cookies()
                logger.info("Browser cookies cleared")
                
        except Exception as e:
            logger.error(f"Failed to clear cookies: {str(e)}")

    def resolve_geo_id_from_location(self, location: str) -> str | None:
        """Resolve LinkedIn geoId for a human-readable location (country/region).

        Strategy:
        1. Try a static map for common locations (worldwide, US, UK, Canada, Nigeria, UAE, etc.).
        2. Fallback: use the Jobs UI location box to trigger a search and
           parse the resulting geoId from the URL query string.
        """
        if not location:
            return None

        if not self.driver:
            logger.error("WebDriver is not initialized. Call login() first.")
            return None

        loc_norm = location.strip().lower()

        # Common geoIds from your examples and useful defaults
        geo_map = {
            # Worldwide
            "world": "92000000",
            "worldwide": "92000000",
            "global": "92000000",
            "anywhere": "92000000",

            # United States
            "us": "103644278",
            "usa": "103644278",
            "united states": "103644278",
            "united states of america": "103644278",

            # United Kingdom
            "uk": "101165590",
            "u.k.": "101165590",
            "united kingdom": "101165590",
            "great britain": "101165590",

            # Canada
            "canada": "101174742",

            # Nigeria
            "nigeria": "105365761",

            # United Arab Emirates
            "united arab emirates": "104305776",
            "united arab emirate": "104305776",
            "uae": "104305776",
        }

        if loc_norm in geo_map:
            return geo_map[loc_norm]

        return None

    def search_jobs(self, keyword: str,
                    location_scope: str = "worldwide",
                    remote: bool = True,
                    onsite: bool = False,
                    easy_apply: bool = True,
                    time_filter: int = 86400):
        """Search for jobs by constructing a LinkedIn Jobs URL.

        Uses URL parameters instead of clicking in the UI, following
        patterns like:
        - Python developer worldwide:
          https://www.linkedin.com/jobs/search/?geoId=92000000&keywords=python%20developer
        - Software engineer US:
          https://www.linkedin.com/jobs/search/?geoId=103644278&keywords=software%20engineer
        - Remote only: add f_WT=2
        - Onsite only: add f_WT=1
        - Easy apply only: add f_AL=true
        """
        try:
            if not self.driver:
                logger.error("WebDriver is not initialized. Call login() first.")
                return False

            # Resolve geoId from a human-readable location/country name
            geo_id = None
            scope_norm = (location_scope or "").strip()
            if scope_norm:
                geo_id = self.resolve_geo_id_from_location(scope_norm)

            params: dict[str, str] = {
                "keywords": keyword,
                "origin": "JOB_SEARCH_PAGE_JOB_FILTER",
                "refresh": "true",
            }

            if geo_id:
                params["geoId"] = geo_id

            # Work type filter: 1 = onsite, 2 = remote
            if remote is True:
                params["f_WT"] = "2"
            elif onsite is True:
                params["f_WT"] = "1"

            if easy_apply:
                params["f_AL"] = "true"
            if time_filter:
                params["f_TPR"] = f"r{time_filter}"

            query = urlencode(params, quote_via=quote_plus)
            search_url = f"{self.jobs_url}search/?{query}"

            logger.info(f"Navigating to search URL: {search_url}")
            self.driver.get(search_url)

            # Wait for at least one job card to appear (by XPath)
            self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//li[contains(@class, 'scaffold-layout__list-item') or contains(@class, 'jobs-search-results__list-item')]"
                    )
                )
            )

            logger.info("Job search completed and results loaded.")
            return True
        except Exception as e:
            logger.error(f"Failed to search jobs: {str(e)}")
            return False

    def select_jobs(self, max_job=5):
        """
        Select up to max_job job cards from the search results.

        Priority order:
        1) "You'd be a top applicant"
        2) "Actively reviewing applicants"
        3) Everything else
        Returns a list of job IDs for the selected jobs.
        """
        if not self.driver:
            logger.error("WebDriver is not initialized. Call login() first.")
            return []

        try:
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.scaffold-layout__list-item, li.jobs-search-results__list-item"))
            )
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "li.scaffold-layout__list-item, li.jobs-search-results__list-item")
            if not job_cards:
                logger.warning("No job cards found on the page.")
                return []

            top_applicant = []
            actively_reviewing = []
            others = []
            seen_job_ids = set()

            def add_unique(target_list, job_id):
                if job_id and job_id not in seen_job_ids:
                    seen_job_ids.add(job_id)
                    target_list.append(job_id)

            for card in job_cards:
                job_id = None
                try:
                    job_id = card.get_attribute("data-occludable-job-id")
                    insight_elems = card.find_elements(By.CSS_SELECTOR, ".job-card-container__job-insight-text")

                    insight_texts = []
                    for elem in insight_elems:
                        try:
                            text = (elem.text or "").strip().lower().replace("’", "'")
                            if text:
                                insight_texts.append(text)
                        except Exception:
                            continue

                    is_top_applicant = any("top applicant" in t for t in insight_texts)
                    is_actively_reviewing = any("actively reviewing applicants" in t for t in insight_texts)

                    if is_top_applicant:
                        add_unique(top_applicant, job_id)
                    elif is_actively_reviewing:
                        add_unique(actively_reviewing, job_id)
                    else:
                        add_unique(others, job_id)
                except Exception:
                    if job_id is None:
                        try:
                            job_id = card.get_attribute("data-occludable-job-id")
                        except Exception:
                            job_id = None
                    add_unique(others, job_id)

            selected = top_applicant[:max_job]
            if len(selected) < max_job:
                selected += actively_reviewing[:max_job - len(selected)]
            if len(selected) < max_job:
                selected += others[:max_job - len(selected)]

            logger.info(
                f"Selected {len(selected)} job IDs (priority: 'You\'d be a top applicant' -> 'Actively reviewing applicants')."
            )
            return selected
        except Exception as e:
            logger.error(f"Error selecting jobs: {str(e)}")
            return []

    def get_job_description(self):
        """
        Extracts the job description HTML/text from the currently loaded job page.
        Returns the job description as a string, or None if not found.
        """
        if not self.driver:
            logger.error("WebDriver is not initialized. Call login() first.")
            return None

        try:
            # Wait for the job description element to be present
            desc_elem = self.wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div.jobs-description__content div#job-details"
                ))
            )
            # Get the inner HTML (preserves formatting and lists)
            job_desc_html = desc_elem.get_attribute("innerHTML")
            # Optionally, also get the plain text:
            job_desc_text = desc_elem.text
            logger.info("Job description successfully extracted.")
            return job_desc_text.strip() if job_desc_text else job_desc_html
        except Exception as e:
            logger.error(f"Failed to extract job description: {str(e)}")
            return None

    def get_form_questions(self, max_steps: int = 12, autofill_required: bool = True) -> dict[str, dict[str, Any]]:
        """Collect Easy Apply form fields across steps.

        This method expects the Easy Apply modal to already be open.

        It will:
        1) Extract each field's label, whether it is required, and what values it can take.
        2) Attempt to fill *empty required* fields with reasonable defaults/placeholders.
        3) Click "Next" repeatedly until a "Review" button is present (or until a safety limit).

                Returns:
                        JSON-serializable dict in the shape:
                        {
                            "Some label": {
                                "input_type": "text" | "textarea" | "checkbox" | "radio",
                                "acceptable_values": null | ["Option 1", "Option 2", ...],
                                "is_required": true | false
                            },
                            ...
                        }
        """

        if not self.driver:
            logger.error("WebDriver is not initialized. Call login() first.")
            return {}

        if self.wait is None:
            self.wait = WebDriverWait(self.driver, 10)

        # Best-effort defaults for common fields (falls back to env, then placeholders).
        default_first_name = ""
        default_last_name = ""
        default_email = (self.email or "").strip()
        default_phone = ""
        default_country = ""
        default_city = ""
        default_street = ""
        default_state = ""
        default_zip = ""
        default_dob = ""

        try:
            from configuration import personal as personal_cfg  # type: ignore

            default_first_name = (getattr(personal_cfg, "first_name", "") or "").strip()
            default_last_name = (getattr(personal_cfg, "last_name", "") or "").strip()
            default_email = (getattr(personal_cfg, "email_address", "") or default_email or "").strip()
            default_phone = (getattr(personal_cfg, "phone_number", "") or "").strip()
            default_country = (getattr(personal_cfg, "country", "") or "").strip()
            default_city = (getattr(personal_cfg, "current_city", "") or "").strip()
            default_street = (getattr(personal_cfg, "street", "") or "").strip()
            default_state = (getattr(personal_cfg, "state", "") or "").strip()
            default_zip = (getattr(personal_cfg, "zipcode", "") or "").strip()
            default_dob = (getattr(personal_cfg, "date_of_birth", "") or "").strip()
        except Exception:
            # If personal config isn't importable, just continue with env/placeholder defaults.
            pass

        def _norm(text: str | None) -> str:
            return (text or "").strip().lower().replace("’", "'")

        def _is_truthy_attr(value: str | None) -> bool:
            return value is not None and str(value).strip().lower() not in ("false", "0", "none", "")

        def _is_required(control, container=None) -> bool:
            try:
                if control is None:
                    return False
                if _is_truthy_attr(control.get_attribute("required")):
                    return True
                if (control.get_attribute("aria-required") or "").strip().lower() == "true":
                    return True
                if container is not None:
                    # Some LinkedIn components indicate required via CSS classes on wrappers/labels.
                    cont_class = _norm(container.get_attribute("class"))
                    if "required" in cont_class and ("state-required" in cont_class or "is-required" in cont_class):
                        return True
                    for lab in container.find_elements(By.CSS_SELECTOR, "label"):
                        if "is-required" in _norm(lab.get_attribute("class")):
                            return True
            except Exception:
                return False
            return False

        def _get_label_for_control(control, form_el, container=None) -> str:
            try:
                el_id = (control.get_attribute("id") or "").strip()
                if el_id:
                    labels = form_el.find_elements(By.CSS_SELECTOR, f"label[for='{el_id}']")
                    if labels:
                        txt = (labels[0].text or "").strip()
                        if txt:
                            return txt
            except Exception:
                pass

            # Try nearest ancestor label
            try:
                lab = control.find_element(By.XPATH, "ancestor::label[1]")
                txt = (lab.text or "").strip()
                if txt:
                    return txt
            except Exception:
                pass

            # Try any label within the same form-element container
            if container is not None:
                try:
                    labs = container.find_elements(By.CSS_SELECTOR, "label")
                    for lab in labs:
                        txt = (lab.text or "").strip()
                        if txt:
                            return txt
                except Exception:
                    pass

            # Fallbacks
            aria = (control.get_attribute("aria-label") or "").strip()
            if aria:
                return aria

            placeholder = (control.get_attribute("placeholder") or "").strip()
            if placeholder:
                return placeholder

            name = (control.get_attribute("name") or "").strip()
            return name

        def _get_group_label_for_choice(container) -> str:
            """Get the question/group label for radio/checkbox controls."""
            if container is None:
                return ""

            selectors = (
                "label[data-test-text-entity-list-form-title]",
                "label.fb-dash-form-element__label",
                "legend",
            )
            for sel in selectors:
                try:
                    labels = container.find_elements(By.CSS_SELECTOR, sel)
                except Exception:
                    labels = []
                for lab in labels:
                    try:
                        txt = (lab.text or "").strip()
                        if txt:
                            return txt
                    except Exception:
                        continue

            # Fallback: first non-empty visible label in container.
            try:
                labels = container.find_elements(By.CSS_SELECTOR, "label")
            except Exception:
                labels = []
            for lab in labels:
                try:
                    txt = (lab.text or "").strip()
                    if txt:
                        return txt
                except Exception:
                    continue

            return ""

        def _get_step_title(form_el) -> str:
            for sel in ("h1", "h2", "h3"):
                try:
                    headers = form_el.find_elements(By.CSS_SELECTOR, sel)
                    for h in headers:
                        if h.is_displayed():
                            txt = (h.text or "").strip()
                            if txt:
                                return txt
                except Exception:
                    continue
            return ""

        def _clean_label(label: str) -> str:
            # LinkedIn sometimes repeats label text on separate lines.
            lines = [ln.strip() for ln in (label or "").splitlines() if ln.strip()]
            if not lines:
                return ""
            if len(lines) >= 2 and all(_norm(ln) == _norm(lines[0]) for ln in lines[1:]):
                return lines[0]
            # Join remaining lines with a single space for stable JSON keys.
            return " ".join(lines)

        def _find_easy_apply_form():
            selectors = (
                "div.jobs-easy-apply-content form",
                "div.jobs-easy-apply-modal form",
                "div[role='dialog'] form",
                "form",
            )
            for sel in selectors:
                try:
                    forms = self.driver.find_elements(By.CSS_SELECTOR, sel)
                except Exception:
                    forms = []
                for f in forms:
                    try:
                        if not f.is_displayed():
                            continue
                        if f.find_elements(
                            By.CSS_SELECTOR,
                            "[data-easy-apply-next-button], [data-live-test-easy-apply-review-button], [data-live-test-easy-apply-submit-button], [data-test-form-element]",
                        ):
                            return f
                    except Exception:
                        continue
            return None

        def _select_first_non_placeholder(
            select_el,
            preferred_contains: str | None = None,
            auto_select: bool = True,
        ) -> list[dict[str, str]]:
            options: list[dict[str, str]] = []
            try:
                sel = Select(select_el)
                for opt in sel.options:
                    label = (opt.text or "").strip()
                    value = (opt.get_attribute("value") or "").strip()
                    options.append({"label": label, "value": value})

                if not options:
                    return options

                current_text = ""
                try:
                    current_text = (sel.first_selected_option.text or "").strip()
                except Exception:
                    current_text = ""

                # Only select if the current selection looks like a placeholder.
                if auto_select and (
                    _norm(current_text).startswith("select") or not (select_el.get_attribute("value") or "").strip()
                ):
                    preferred_norm = _norm(preferred_contains)

                    def is_placeholder(opt_dict: dict[str, str]) -> bool:
                        t = _norm(opt_dict.get("label"))
                        v = _norm(opt_dict.get("value"))
                        return t.startswith("select") or v.startswith("select")

                    chosen: dict[str, str] | None = None
                    if preferred_norm:
                        for opt_dict in options:
                            if is_placeholder(opt_dict):
                                continue
                            if preferred_norm in _norm(opt_dict.get("label")) or preferred_norm in _norm(opt_dict.get("value")):
                                chosen = opt_dict
                                break

                    if chosen is None:
                        for opt_dict in options:
                            if not is_placeholder(opt_dict):
                                chosen = opt_dict
                                break

                    if chosen is not None:
                        try:
                            sel.select_by_visible_text(chosen["label"])
                        except Exception:
                            try:
                                sel.select_by_value(chosen["value"])
                            except Exception:
                                pass
            except Exception:
                # If it's not a real <select>, we still try to harvest <option> tags.
                try:
                    for opt in select_el.find_elements(By.CSS_SELECTOR, "option"):
                        options.append({
                            "label": (opt.text or "").strip(),
                            "value": (opt.get_attribute("value") or "").strip(),
                        })
                except Exception:
                    pass
            return options

        def _fill_text_like(control, label_text: str, input_type: str):
            if (control.get_attribute("disabled") or "").strip() or (control.get_attribute("readonly") or "").strip():
                return

            current_value = (control.get_attribute("value") or "").strip()
            if current_value:
                return

            label_norm = _norm(label_text)
            chosen = ""

            if "first name" in label_norm:
                chosen = default_first_name or "Test"
            elif "last name" in label_norm:
                chosen = default_last_name or "User"
            elif "email" in label_norm:
                chosen = default_email or "test@example.com"
            elif "phone" in label_norm:
                digits = "".join(ch for ch in (default_phone or "") if ch.isdigit())
                chosen = digits or "0000000000"
            elif "zip" in label_norm or "postal" in label_norm:
                chosen = default_zip or "00000"
            elif "street" in label_norm or "address" in label_norm:
                chosen = default_street or "N/A"
            elif "city" in label_norm:
                chosen = default_city or "N/A"
            elif "state" in label_norm or "province" in label_norm:
                chosen = default_state or "N/A"
            elif "country" in label_norm:
                chosen = default_country or "N/A"
            elif "date of birth" in label_norm or "birth" in label_norm:
                chosen = default_dob or "2000-01-01"
            elif "year" or "hour" in label_norm:
                chosen = "1"
            elif "hrs" or "hours" in label_norm:
                chosen = "1"
            else:
                # Fallback by input type.
                if input_type == "email":
                    chosen = default_email or "test@example.com"
                elif input_type in ("tel", "phone"):
                    digits = "".join(ch for ch in (default_phone or "") if ch.isdigit())
                    chosen = digits or "0000000000"
                elif input_type in ("number",):
                    chosen = "1"
                elif input_type in ("date",):
                    chosen = default_dob or "2000-01-01"
                else:
                    chosen = "N/A"

            try:
                control.click()
            except Exception:
                pass

            try:
                control.clear()
            except Exception:
                try:
                    control.send_keys(Keys.CONTROL + "a")
                    control.send_keys(Keys.BACK_SPACE)
                except Exception:
                    pass

            try:
                control.send_keys(chosen)
            except Exception:
                # Last resort: set via JS.
                try:
                    self.driver.execute_script("arguments[0].value = arguments[1];", control, chosen)
                except Exception:
                    pass

        def _click_control(control) -> bool:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", control)
            except Exception:
                pass

            try:
                control.click()
                return True
            except Exception:
                pass

            try:
                self.driver.execute_script("arguments[0].click();", control)
                return True
            except Exception:
                return False

        def _ensure_default_radio_selected(container, form_el, group_name: str = "") -> bool:
            try:
                radios = container.find_elements(By.CSS_SELECTOR, "input[type='radio']")
            except Exception:
                return False

            if not radios:
                return False

            group_name_norm = _norm(group_name)
            if group_name_norm:
                scoped_radios = []
                for radio in radios:
                    try:
                        if _norm(radio.get_attribute("name")) == group_name_norm:
                            scoped_radios.append(radio)
                    except Exception:
                        continue
                if scoped_radios:
                    radios = scoped_radios

            for radio in radios:
                try:
                    if radio.is_selected():
                        return True
                except Exception:
                    continue

            for radio in radios:
                try:
                    if not radio.is_enabled():
                        continue
                except Exception:
                    pass

                if _click_control(radio):
                    try:
                        if radio.is_selected():
                            return True
                    except Exception:
                        return True

                radio_id = (radio.get_attribute("id") or "").strip()
                if radio_id:
                    try:
                        labels = form_el.find_elements(By.CSS_SELECTOR, f"label[for='{radio_id}']")
                    except Exception:
                        labels = []
                    for label_el in labels:
                        if _click_control(label_el):
                            try:
                                if radio.is_selected():
                                    return True
                            except Exception:
                                return True

            return False

        def _fill_required_fields(form_el) -> list[dict[str, Any]]:
            extracted: list[dict[str, Any]] = []
            seen: set[tuple[int, str, str, str]] = set()
            processed_radio_groups: set[str] = set()

            step_title = _get_step_title(form_el)

            containers = []
            try:
                containers = form_el.find_elements(By.CSS_SELECTOR, "[data-test-form-element]")
            except Exception:
                containers = []

            if not containers:
                containers = [form_el]

            for container in containers:
                try:
                    controls = container.find_elements(By.CSS_SELECTOR, "input, select, textarea")
                except Exception:
                    controls = []

                for control in controls:
                    try:
                        tag = (control.tag_name or "").lower()
                        if tag not in ("input", "select", "textarea"):
                            continue

                        input_type = ""
                        if tag == "input":
                            input_type = ((control.get_attribute("type") or "text").strip().lower())
                            if input_type == "hidden":
                                continue

                        el_id = (control.get_attribute("id") or "").strip()
                        name = (control.get_attribute("name") or "").strip()
                        option_label = ""
                        if tag == "input" and input_type in ("radio", "checkbox"):
                            option_label = _get_label_for_control(control, form_el, container=container)
                            group_label = _get_group_label_for_choice(container)
                            label = group_label or option_label
                        else:
                            label = _get_label_for_control(control, form_el, container=container)
                        required = _is_required(control, container=container)

                        key = (step_index, tag, el_id or name, _norm(label))
                        if key in seen:
                            continue
                        seen.add(key)

                        entry: dict[str, Any] = {
                            "step": step_index,
                            "step_title": step_title,
                            "label": label,
                            "required": required,
                            "tag": tag,
                            "id": el_id,
                            "name": name,
                        }

                        if tag == "select":
                            options = _select_first_non_placeholder(
                                control,
                                preferred_contains=(
                                    default_country if "country code" in _norm(label) or "country" in _norm(label) else None
                                ),
                                auto_select=(autofill_required and required),
                            )
                            entry["options"] = options
                        elif tag == "textarea":
                            entry["input_type"] = "textarea"
                        else:
                            entry["input_type"] = input_type
                            entry["inputmode"] = (control.get_attribute("inputmode") or "").strip()
                            entry["pattern"] = (control.get_attribute("pattern") or "").strip()
                            entry["min"] = (control.get_attribute("min") or "").strip()
                            entry["max"] = (control.get_attribute("max") or "").strip()
                            entry["maxlength"] = (control.get_attribute("maxlength") or "").strip()
                            if input_type in ("radio", "checkbox"):
                                entry["option_label"] = option_label
                            if input_type == "file":
                                entry["accept"] = (control.get_attribute("accept") or "").strip()

                        extracted.append(entry)

                        # Auto-fill empty required fields so we can proceed to the next step.
                        if autofill_required:
                            if input_type == "radio":
                                group_name = (name or el_id or label or "").strip()
                                group_key = _norm(name) or _norm(el_id) or _norm(label) or f"radio-{step_index}-{len(processed_radio_groups)}"
                                if group_key not in processed_radio_groups:
                                    _ensure_default_radio_selected(container, form_el, group_name=(name or "").strip())
                                    processed_radio_groups.add(group_key)
                            elif not required:
                                # Required autofill only beyond this point.
                                pass
                            elif tag == "select":
                                # selection handled inside _select_first_non_placeholder
                                pass
                            elif tag == "textarea":
                                if (control.get_attribute("value") or "").strip() or (control.text or "").strip():
                                    continue
                                _fill_text_like(control, label, "text")
                            else:
                                if input_type == "checkbox":
                                    try:
                                        if not control.is_selected():
                                            control.click()
                                    except Exception:
                                        pass
                                elif input_type == "file":
                                    # File upload can't be safely guessed; leave it as-is.
                                    # The field will be reported in the returned schema.
                                    pass
                                else:
                                    _fill_text_like(control, label, input_type)
                    except Exception:
                        continue

            return extracted

        schema: dict[str, dict[str, Any]] = {}
        max_steps = max(1, int(max_steps))
        stuck_count = 0
        last_step_fingerprint = ""

        def _simplify_input_type(entry: dict[str, Any]) -> str:
            tag = (entry.get("tag") or "").lower()
            if tag == "textarea":
                return "textarea"
            if tag == "input":
                it = (entry.get("input_type") or "").strip().lower()
                if it in ("checkbox", "radio"):
                    return it
                return "text"
            if tag == "select":
                # Treat selects as "text" per requested output schema; acceptable_values will include options.
                return "text"
            return "text"

        def _acceptable_values(entry: dict[str, Any], limit: int = 10) -> list[str] | None:
            tag = (entry.get("tag") or "").lower()
            if tag == "select":
                opts = entry.get("options") or []
                labels: list[str] = []
                for o in opts:
                    try:
                        if isinstance(o, dict):
                            label = (o.get("label") or "").strip()
                        else:
                            label = str(o).strip()
                    except Exception:
                        continue
                    if not label:
                        continue
                    if _norm(label).startswith("select"):
                        continue
                    labels.append(label)

                # De-duplicate while preserving order
                seen_vals: set[str] = set()
                unique_labels: list[str] = []
                for lab in labels:
                    if lab in seen_vals:
                        continue
                    seen_vals.add(lab)
                    unique_labels.append(lab)
                if not unique_labels:
                    return None
                return unique_labels[: max(1, int(limit))]

            input_type = (entry.get("input_type") or "").strip().lower()
            if input_type in ("radio", "checkbox"):
                option = (entry.get("option_label") or "").strip()
                label = (entry.get("label") or "").strip()
                if option and _norm(option) != _norm(label):
                    return [option]
                return None

            if input_type == "file":
                accept = (entry.get("accept") or "").strip()
                if not accept:
                    return None
                vals = [a.strip() for a in accept.split(",") if a.strip()]
                if not vals:
                    return None
                return vals[: max(1, int(limit))]

            return None

        def _merge_schema(label: str, item: dict[str, Any]):
            if label not in schema:
                schema[label] = item
                return

            existing = schema[label]
            # Required: if any occurrence says required, keep it required.
            existing["is_required"] = bool(existing.get("is_required")) or bool(item.get("is_required"))

            # Acceptable values: union while preserving order.
            ev = existing.get("acceptable_values")
            iv = item.get("acceptable_values")
            if ev is None and iv is not None:
                if isinstance(iv, list):
                    existing["acceptable_values"] = iv[:10]
                else:
                    existing["acceptable_values"] = iv
            elif isinstance(ev, list) and isinstance(iv, list):
                seen_union = set(ev)
                for v in iv:
                    if v not in seen_union:
                        ev.append(v)
                        seen_union.add(v)
                if len(ev) > 10:
                    del ev[10:]

            # Input type: prefer non-text if there's a conflict.
            if existing.get("input_type") == "text" and item.get("input_type") in ("textarea", "checkbox", "radio"):
                existing["input_type"] = item.get("input_type")

        def _find_back_button():
            selectors = (
                "button[aria-label='Back to previous step']",
                "button[aria-label*='Back to previous step']",
                "button[data-easy-apply-back-button]",
                "button:has(span):not([disabled])",
            )
            for sel in selectors:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                except Exception:
                    btns = []
                for b in btns:
                    try:
                        if not b.is_displayed():
                            continue
                        aria = _norm(b.get_attribute("aria-label"))
                        txt = _norm(b.text)
                        if "back" in aria or aria == "back to previous step" or txt == "back":
                            return b
                    except Exception:
                        continue
            return None

        def _go_back_to_initial_step(max_back_clicks: int = 20):
            # Click "Back" until it disappears or becomes disabled.
            for _ in range(max(1, int(max_back_clicks))):
                back_btn = _find_back_button()
                if back_btn is None:
                    return
                try:
                    if not back_btn.is_enabled():
                        return
                except Exception:
                    pass

                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", back_btn)
                except Exception:
                    pass

                try:
                    self.driver.execute_script("arguments[0].click();", back_btn)
                except Exception:
                    try:
                        back_btn.click()
                    except Exception:
                        return

                self.random_delay(1.0, 2.0)

        for step_index in range(1, max_steps + 1):
            form_el = _find_easy_apply_form()
            if form_el is None:
                try:
                    self.wait.until(lambda d: _find_easy_apply_form() is not None)
                except Exception:
                    logger.error("Easy Apply form not found. Make sure the Easy Apply modal is open.")
                    break
                form_el = _find_easy_apply_form()
                if form_el is None:
                    break

            # Extract + (optionally) auto-fill
            extracted = _fill_required_fields(form_el)
            for entry in extracted:
                try:
                    raw_label = _clean_label((entry.get("label") or "").strip())
                    label_key = raw_label
                    if not label_key:
                        label_key = (entry.get("name") or entry.get("id") or "").strip() or "Unknown"

                    schema_item = {
                        "input_type": _simplify_input_type(entry),
                        "acceptable_values": _acceptable_values(entry, limit=10),
                        "is_required": bool(entry.get("required")),
                    }
                    _merge_schema(label_key, schema_item)
                except Exception:
                    continue

            # Stop condition: review button present
            try:
                review_btns = form_el.find_elements(By.CSS_SELECTOR, "button[data-live-test-easy-apply-review-button], button[aria-label*='Review']")
                review_btn = next((b for b in review_btns if b.is_displayed()), None)
            except Exception:
                review_btn = None
            if review_btn is not None:
                logger.info("Reached Easy Apply review step (Review button present).")
                # Click Review (do not submit), then go back to the initial step.
                try:
                    if review_btn.is_enabled():
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", review_btn)
                        except Exception:
                            pass
                        try:
                            self.driver.execute_script("arguments[0].click();", review_btn)
                        except Exception:
                            review_btn.click()
                        self.random_delay(1.5, 3.0)
                        _go_back_to_initial_step(max_back_clicks=max_steps + 5)
                except Exception:
                    # Even if review click fails, still try to go back if possible.
                    try:
                        _go_back_to_initial_step(max_back_clicks=max_steps + 5)
                    except Exception:
                        pass
                break

            # Find Next button
            next_btn = None
            try:
                candidates = form_el.find_elements(
                    By.CSS_SELECTOR,
                    "button[data-easy-apply-next-button], button[aria-label*='Continue to next step'], button[aria-label='Next']",
                )
                for b in candidates:
                    if b.is_displayed():
                        next_btn = b
                        break
            except Exception:
                next_btn = None

            if next_btn is None:
                logger.info("No Next button found; stopping form traversal.")
                break

            if not next_btn.is_enabled():
                # Avoid infinite loops if a required field cannot be filled (e.g., resume upload).
                logger.warning("Next button is disabled; stopping form traversal.")
                break

            # Fingerprint the current step to detect getting stuck.
            try:
                step_title = _get_step_title(form_el)
                first_label = extracted[0]["label"] if extracted else ""
                fingerprint = f"{step_title}|{first_label}|{len(extracted)}"
            except Exception:
                fingerprint = ""

            if fingerprint and fingerprint == last_step_fingerprint:
                stuck_count += 1
            else:
                stuck_count = 0
                last_step_fingerprint = fingerprint

            if stuck_count >= 2:
                logger.warning("Detected repeated Easy Apply step; stopping to avoid an infinite loop.")
                break

            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
            except Exception:
                pass

            try:
                self.driver.execute_script("arguments[0].click();", next_btn)
            except Exception:
                try:
                    next_btn.click()
                except Exception:
                    logger.warning("Failed to click Next button; stopping form traversal.")
                    break

            # Give the next step time to load.
            self.random_delay(1.5, 3.0)

        return schema

    def fill_form_questions(
        self,
        answers: dict[str, Any] | str,
        resume_pdf_path: str | None = None,
        max_steps: int = 12,
    ) -> bool:
        """Fill Easy Apply questions using answers returned by the LLM.

        The input may be either a parsed dict or a JSON string mapping question labels
        to answer strings (or arrays for checkbox-style questions).
        """
        if not self.driver:
            logger.error("WebDriver is not initialized. Call login() first.")
            return False

        if self.wait is None:
            self.wait = WebDriverWait(self.driver, 10)

        def _norm(text: str | None) -> str:
            return (text or "").strip().lower().replace("’", "'")

        def _clean_label(label: str) -> str:
            lines = [ln.strip() for ln in (label or "").splitlines() if ln.strip()]
            if not lines:
                return ""
            if len(lines) >= 2 and all(_norm(ln) == _norm(lines[0]) for ln in lines[1:]):
                return lines[0]
            return " ".join(lines)

        def _strip_code_fences(text: str) -> str:
            stripped = (text or "").strip()
            if stripped.startswith("```"):
                lines = stripped.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                stripped = "\n".join(lines).strip()
            return stripped

        def _extract_json_object(text: str) -> str:
            stripped = _strip_code_fences(text)
            if not stripped:
                return ""
            start = stripped.find("{")
            end = stripped.rfind("}")
            if start != -1 and end != -1 and end > start:
                return stripped[start:end + 1]
            return stripped

        def _answer_values(value: Any) -> list[str]:
            if value is None:
                return []
            if isinstance(value, bool):
                return ["Yes" if value else "No"]
            if isinstance(value, (int, float)):
                return [str(value)]
            if isinstance(value, str):
                text = value.strip()
                return [text] if text else []
            if isinstance(value, list):
                values: list[str] = []
                for item in value:
                    values.extend(_answer_values(item))
                return values
            if isinstance(value, dict):
                for key in ("answer", "value", "text", "selection", "selected", "answers"):
                    if key in value:
                        return _answer_values(value[key])
                return []
            text = str(value).strip()
            return [text] if text else []

        def _parse_answers(raw_answers: dict[str, Any] | str) -> dict[str, list[str]]:
            parsed: dict[str, Any] = {}
            if isinstance(raw_answers, dict):
                parsed = raw_answers
            elif isinstance(raw_answers, str):
                raw_text = _extract_json_object(raw_answers)
                if not raw_text:
                    return {}
                try:
                    decoded = json.loads(raw_text)
                    if isinstance(decoded, dict):
                        parsed = decoded
                except json.JSONDecodeError as parse_error:
                    logger.error(f"Failed to parse LLM answers as JSON: {parse_error}")
                    return {}
            else:
                return {}

            normalized: dict[str, list[str]] = {}
            for key, value in parsed.items():
                label = _clean_label(str(key))
                if not label:
                    continue
                values = [item for item in _answer_values(value) if item]
                if values:
                    normalized[_norm(label)] = values
            return normalized

        normalized_answers = _parse_answers(answers)
        if not normalized_answers:
            logger.warning("No valid LLM answers were available; attempting resume upload and step navigation only.")

        resolved_resume_pdf_path = None
        if resume_pdf_path:
            candidate_path = os.path.abspath(resume_pdf_path)
            if os.path.exists(candidate_path):
                resolved_resume_pdf_path = candidate_path
            else:
                logger.warning(f"Resume PDF path does not exist: {candidate_path}")

        def _find_easy_apply_form():
            selectors = (
                "div.jobs-easy-apply-content form",
                "div.jobs-easy-apply-modal form",
                "div[role='dialog'] form",
                "form",
            )
            for sel in selectors:
                try:
                    forms = self.driver.find_elements(By.CSS_SELECTOR, sel)
                except Exception:
                    forms = []
                for form in forms:
                    try:
                        if not form.is_displayed():
                            continue
                        if form.find_elements(
                            By.CSS_SELECTOR,
                            "[data-easy-apply-next-button], [data-live-test-easy-apply-review-button], [data-test-form-element]",
                        ):
                            return form
                    except Exception:
                        continue
            return None

        def _get_label_for_control(control, form_el, container=None) -> str:
            try:
                el_id = (control.get_attribute("id") or "").strip()
                if el_id:
                    labels = form_el.find_elements(By.CSS_SELECTOR, f"label[for='{el_id}']")
                    if labels:
                        txt = (labels[0].text or "").strip()
                        if txt:
                            return txt
            except Exception:
                pass

            try:
                lab = control.find_element(By.XPATH, "ancestor::label[1]")
                txt = (lab.text or "").strip()
                if txt:
                    return txt
            except Exception:
                pass

            if container is not None:
                try:
                    labels = container.find_elements(By.CSS_SELECTOR, "label")
                except Exception:
                    labels = []
                for lab in labels:
                    try:
                        txt = (lab.text or "").strip()
                        if txt:
                            return txt
                    except Exception:
                        continue

            aria = (control.get_attribute("aria-label") or "").strip()
            if aria:
                return aria
            placeholder = (control.get_attribute("placeholder") or "").strip()
            if placeholder:
                return placeholder
            return (control.get_attribute("name") or "").strip()

        def _get_group_label_for_choice(container) -> str:
            if container is None:
                return ""

            selectors = (
                "label[data-test-text-entity-list-form-title]",
                "label.fb-dash-form-element__label",
                "legend",
            )
            for sel in selectors:
                try:
                    labels = container.find_elements(By.CSS_SELECTOR, sel)
                except Exception:
                    labels = []
                for lab in labels:
                    try:
                        txt = (lab.text or "").strip()
                        if txt:
                            return txt
                    except Exception:
                        continue

            try:
                labels = container.find_elements(By.CSS_SELECTOR, "label")
            except Exception:
                labels = []
            for lab in labels:
                try:
                    txt = (lab.text or "").strip()
                    if txt:
                        return txt
                except Exception:
                    continue
            return ""

        def _set_text_value(control, value: str):
            try:
                control.click()
            except Exception:
                pass

            try:
                control.clear()
            except Exception:
                try:
                    control.send_keys(Keys.CONTROL + "a")
                    control.send_keys(Keys.BACK_SPACE)
                except Exception:
                    pass

            try:
                control.send_keys(value)
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].value = arguments[1];", control, value)
                except Exception:
                    pass

        def _try_upload_file(control, file_path: str) -> bool:
            try:
                control.send_keys(file_path)
                return True
            except Exception:
                pass

            try:
                self.driver.execute_script(
                    "arguments[0].removeAttribute('disabled');"
                    "arguments[0].removeAttribute('readonly');"
                    "arguments[0].style.display='block';"
                    "arguments[0].style.visibility='visible';"
                    "arguments[0].style.opacity=1;"
                    "arguments[0].style.height='1px';"
                    "arguments[0].style.width='1px';",
                    control,
                )
                control.send_keys(file_path)
                return True
            except Exception:
                return False

        def _control_key(control) -> str:
            try:
                parts = [
                    (control.get_attribute("id") or "").strip(),
                    (control.get_attribute("name") or "").strip(),
                    (control.get_attribute("aria-label") or "").strip(),
                    getattr(control, "id", ""),
                ]
                return "|".join(parts)
            except Exception:
                return ""

        def _click_element(element) -> bool:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            except Exception:
                pass

            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                try:
                    element.click()
                    return True
                except Exception:
                    return False

        def _select_answer(select_el, answer_values: list[str]) -> bool:
            if not answer_values:
                return False
            answer_norms = [_norm(v) for v in answer_values if v]
            try:
                select_obj = Select(select_el)
            except Exception:
                return False

            options = []
            for option in select_obj.options:
                label = (option.text or "").strip()
                value = (option.get_attribute("value") or "").strip()
                if not label and not value:
                    continue
                if _norm(label).startswith("select") or _norm(value).startswith("select"):
                    continue
                options.append((option, label, value))

            for answer_norm, answer_value in zip(answer_norms, answer_values):
                for _, label, value in options:
                    if answer_norm == _norm(label) or answer_norm == _norm(value):
                        try:
                            select_obj.select_by_visible_text(label)
                        except Exception:
                            try:
                                select_obj.select_by_value(value)
                            except Exception:
                                continue
                        return True

                for _, label, value in options:
                    if answer_norm in _norm(label) or answer_norm in _norm(value):
                        try:
                            select_obj.select_by_visible_text(label)
                        except Exception:
                            try:
                                select_obj.select_by_value(value)
                            except Exception:
                                continue
                        return True
            return False

        def _fill_choice_group(form_el, container, answer_values: list[str]) -> bool:
            try:
                choice_controls = container.find_elements(By.CSS_SELECTOR, "input[type='radio'], input[type='checkbox']")
            except Exception:
                choice_controls = []

            if not choice_controls:
                return False

            matched = False
            is_checkbox_group = any(((control.get_attribute("type") or "").strip().lower() == "checkbox") for control in choice_controls)

            def _select_default_radio_in_group() -> bool:
                # Select the first available radio option when no explicit answer is provided.
                for control in choice_controls:
                    try:
                        control_type = (control.get_attribute("type") or "").strip().lower()
                        if control_type != "radio":
                            continue
                    except Exception:
                        continue

                    try:
                        if control.is_selected():
                            return True
                    except Exception:
                        continue

                for control in choice_controls:
                    try:
                        control_type = (control.get_attribute("type") or "").strip().lower()
                        if control_type != "radio":
                            continue
                    except Exception:
                        continue

                    if _click_element(control):
                        try:
                            if control.is_selected():
                                return True
                        except Exception:
                            return True

                    radio_id = (control.get_attribute("id") or "").strip()
                    if radio_id:
                        try:
                            labels = form_el.find_elements(By.CSS_SELECTOR, f"label[for='{radio_id}']")
                        except Exception:
                            labels = []
                        for label_el in labels:
                            if _click_element(label_el):
                                try:
                                    if control.is_selected():
                                        return True
                                except Exception:
                                    return True

                return False

            if not answer_values:
                if is_checkbox_group:
                    return False
                return _select_default_radio_in_group()

            normalized_targets = [_norm(v) for v in answer_values if v]

            for control in choice_controls:
                option_label = _clean_label(_get_label_for_control(control, form_el, container=container))
                option_norm = _norm(option_label)
                if not option_norm:
                    continue

                should_select = any(
                    target == option_norm or target in option_norm or option_norm in target
                    for target in normalized_targets
                )
                if not should_select:
                    continue

                try:
                    if not control.is_selected():
                        if _click_element(control):
                            matched = True
                    else:
                        matched = True
                except Exception:
                    continue

                if matched and not is_checkbox_group:
                    break

            if not matched and not is_checkbox_group:
                matched = _select_default_radio_in_group()

            return matched

        uploaded_file_controls: set[str] = set()

        def _upload_resume_file_inputs(form_el) -> bool:
            if not resolved_resume_pdf_path:
                return False

            uploaded_any = False
            try:
                file_inputs = form_el.find_elements(By.CSS_SELECTOR, "input[type='file']")
            except Exception:
                file_inputs = []

            for file_input in file_inputs:
                key = _control_key(file_input)
                if key and key in uploaded_file_controls:
                    continue

                label = _clean_label(_get_label_for_control(file_input, form_el))
                if _try_upload_file(file_input, resolved_resume_pdf_path):
                    if key:
                        uploaded_file_controls.add(key)
                    logger.info(f"Uploaded tailored resume for field: {label or 'file input'}")
                    uploaded_any = True
                else:
                    logger.warning(f"Could not upload tailored resume for field: {label or 'file input'}")

            return uploaded_any

        max_steps = max(1, int(max_steps))
        for _ in range(max_steps):
            form_el = _find_easy_apply_form()
            if form_el is None:
                logger.error("Easy Apply form not found while filling answers.")
                return False

            uploaded_this_step = _upload_resume_file_inputs(form_el)
            self.random_delay(10, 30)

            try:
                containers = form_el.find_elements(By.CSS_SELECTOR, "[data-test-form-element]")
            except Exception:
                containers = []
            if not containers:
                containers = [form_el]

            for container in containers:
                try:
                    controls = container.find_elements(By.CSS_SELECTOR, "input, select, textarea")
                except Exception:
                    controls = []
                if not controls:
                    continue

                processed_choice_group = False
                for control in controls:
                    try:
                        tag = (control.tag_name or "").lower()
                        if tag not in ("input", "select", "textarea"):
                            continue

                        input_type = ((control.get_attribute("type") or "text").strip().lower()) if tag == "input" else tag
                        if tag == "input" and input_type == "hidden":
                            continue

                        if tag == "input" and input_type in ("radio", "checkbox"):
                            if processed_choice_group:
                                continue
                            group_label = _clean_label(_get_group_label_for_choice(container))
                            if not group_label:
                                group_label = _clean_label(_get_label_for_control(control, form_el, container=container))
                            answer_values = normalized_answers.get(_norm(group_label), [])
                            _fill_choice_group(form_el, container, answer_values)
                            processed_choice_group = True
                            continue

                        label = _clean_label(_get_label_for_control(control, form_el, container=container))
                        if not label:
                            label = (control.get_attribute("name") or control.get_attribute("id") or "").strip()

                        if input_type == "file":
                            if resolved_resume_pdf_path:
                                control_key = _control_key(control)
                                if not control_key or control_key not in uploaded_file_controls:
                                    if _try_upload_file(control, resolved_resume_pdf_path):
                                        if control_key:
                                            uploaded_file_controls.add(control_key)
                                        logger.info(f"Uploaded tailored resume for field: {label}")
                                        uploaded_this_step = True
                                    else:
                                        logger.warning(f"Could not upload tailored resume for field: {label}")
                            continue

                        answer_values = normalized_answers.get(_norm(label), [])
                        if not answer_values:
                            continue

                        if tag == "select":
                            _select_answer(control, answer_values)
                        elif tag == "textarea":
                            _set_text_value(control, answer_values[0])
                        else:
                            _set_text_value(control, answer_values[0])
                    except Exception:
                        continue

            try:
                review_btns = form_el.find_elements(
                    By.CSS_SELECTOR,
                    "button[data-live-test-easy-apply-review-button], button[aria-label*='Review']",
                )
                review_btn = next((btn for btn in review_btns if btn.is_displayed()), None)
            except Exception:
                review_btn = None
            if review_btn is not None:
                clicked = _click_element(review_btn)
                if clicked:
                    self.random_delay(1.5, 3.0)
                return clicked

            next_btn = None
            try:
                next_candidates = form_el.find_elements(
                    By.CSS_SELECTOR,
                    "button[data-easy-apply-next-button], button[aria-label*='Continue to next step'], button[aria-label='Next']",
                )
                next_btn = next((btn for btn in next_candidates if btn.is_displayed()), None)
            except Exception:
                next_btn = None

            if next_btn is None:
                logger.info("No Next button found while filling the form.")
                return False
            if not next_btn.is_enabled():
                if uploaded_this_step:
                    # LinkedIn sometimes enables Next shortly after a successful file upload.
                    self.random_delay(1.0, 1.8)
                    if next_btn.is_enabled() and _click_element(next_btn):
                        self.random_delay(1.5, 3.0)
                        continue
                logger.warning("Next button is disabled after filling answers.")
                return False
            if not _click_element(next_btn):
                logger.warning("Failed to click Next button while filling answers.")
                return False

            self.random_delay(1.5, 3.0)

        logger.warning("Reached fill_form_questions() safety limit before hitting Review.")
        return False

    def submit_application(self):
        """Click the Easy Apply 'Submit application' button on the review step."""
        if not self.driver:
            logger.error("WebDriver is not initialized. Call login() first.")
            return False

        if self.wait is None:
            self.wait = WebDriverWait(self.driver, 10)

        try:
            submit_btn = self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "button[data-live-test-easy-apply-submit-button], button[aria-label*='Submit application']",
                    )
                )
            )

            if not submit_btn.is_displayed() or not submit_btn.is_enabled():
                logger.warning("Submit application button is present but not clickable.")
                return False

            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
            except Exception:
                pass

            try:
                submit_btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", submit_btn)

            self.random_delay(1.5, 3.0)
            logger.info("Clicked 'Submit application' button.")
            return True
        except Exception as e:
            logger.warning(f"Failed to submit application: {str(e)}")
            return False

    def apply_job(self, job_id):
        """
        Navigates to the job page for the given job_id, extracts the job description, and clicks the Easy Apply button if it exists.
        Returns a tuple (easy_apply_clicked: bool, job_description: str|None)
        """
        if not self.driver:
            logger.error("WebDriver is not initialized. Call login() first.")
            return False, None

        job_url = f"https://www.linkedin.com/jobs/search/?currentJobId={job_id}"
        logger.info(f"Navigating to job page: {job_url}")
        self.driver.get(job_url)
        self.random_delay(2, 4)

        job_description = self.get_job_description()

        try:
            # Wait for the Easy Apply button to be present
            easy_apply_btn = self.wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    f"//button[@id='jobs-apply-button-id' and contains(@class, 'jobs-apply-button') and contains(@aria-label, 'Apply')]"
                ))
            )
            if easy_apply_btn and easy_apply_btn.is_displayed() and easy_apply_btn.is_enabled():
                logger.info(f"Easy Apply button found for job {job_id}, clicking...")
                easy_apply_btn.click()
                self.random_delay(1, 2)
                form_schema = self.get_form_questions()
                resume_pdf_path = None
                if tailor_resume:
                    resume_data = generate_tailored_resume_data(job_description or "")
                    if resume_data:
                        safe_job_id = "".join(ch for ch in str(job_id) if ch.isalnum() or ch in ("-", "_")) or "job"
                        # output_path = os.path.join("generated_resumes", f"tailored_resume_{safe_job_id}.pdf")
                        output_path = os.path.join("resume","generated_resumes", f"FAJEMISIN_ADENIYI_RESUME.pdf")
                        try:
                            resume_pdf_path = render_resume_pdf(resume_data, output_path)
                            logger.info(f"Tailored resume generated: {resume_pdf_path}")
                        except Exception as resume_error:
                            logger.warning(f"Failed to generate tailored resume PDF: {resume_error}")
                    else:
                        logger.info("Tailored resume generation returned no content; continuing without resume upload.")
                else:
                    logger.info("TAILOR_RESUME is disabled; skipping tailored resume generation.")

                form_answer = answer_job_question(job_description, form_schema)
                form_filled = self.fill_form_questions(form_answer, resume_pdf_path=resume_pdf_path)
                submitted = False
                if form_filled:
                    submitted = self.submit_application()
                else:
                    logger.info("Form was not fully advanced to review; skipping submit click.")
                try:
                    print(json.dumps(form_schema, indent=2, ensure_ascii=False))
                except Exception:
                    print(form_schema)

                print(f"LLM form answers:\n{form_answer}\n")
                return submitted
            else:
                logger.info(f"Easy Apply button not clickable for job {job_id}.")
                return False
        except Exception as e:
            logger.info(f"Easy Apply button not found for job {job_id}: {str(e)}")
            return False

if __name__ == "__main__":

    bot = LinkedInJobBot(headless=False)
    if bot.login():
        # Example searches using URL parameters:
        # - Worldwide Python developer:
        #   bot.search_jobs(keyword="python developer", location_scope="worldwide")
        # - US software engineer, remote only:
        #   bot.search_jobs(keyword="software engineer", location_scope="us", remote=True)
        # - US software engineer, onsite + easy apply only:
        #   bot.search_jobs(keyword="software engineer", location_scope="us", onsite=True, easy_apply=True)

        # Example: Python developer in UK (any work type, easy apply only)
        # if bot.search_jobs(keyword="python developer", location_scope="uk", remote=True):
        #     # Apply to up to 5 simple one-click Easy Apply jobs
        #     selected_jobs = bot.select_jobs()
        #     logger.info(f"Selected Jobs: {selected_jobs}")

        submitted = bot.apply_job('4373602515')  # Example job ID, replace with actual ID from search results

        # print(f"Job Description: {job_description}")

