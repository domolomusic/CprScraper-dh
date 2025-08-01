import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException, TimeoutException
import logging
import hashlib
import os

logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.monitoring_settings = self.config_loader.get_setting('monitoring_settings')
        self.user_agent = self.monitoring_settings.get('user_agent', 'PayrollMonitor/1.0 (Government Forms Monitoring)')
        self.timeout = self.monitoring_settings.get('timeout_seconds', 30)
        logger.info("WebScraper initialized.")

    def _get_driver(self):
        """Initializes and returns a headless Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={self.user_agent}")
        
        # Attempt to find chromedriver in common paths or rely on PATH
        # This part might need adjustment based on the specific environment
        try:
            # Assumes chromedriver is in PATH or a well-known location
            driver = webdriver.Chrome(options=chrome_options)
        except WebDriverException as e:
            logger.error(f"Failed to initialize Chrome WebDriver. Ensure ChromeDriver is installed and in your PATH. Error: {e}")
            raise
        return driver

    def fetch_content(self, url, use_js_rendering=False):
        """
        Fetches content from a given URL.
        If use_js_rendering is True, uses Selenium for JavaScript-heavy pages.
        """
        logger.info(f"Fetching content from: {url} (JS rendering: {use_js_rendering})")
        headers = {'User-Agent': self.user_agent}

        if use_js_rendering:
            driver = None
            try:
                driver = self._get_driver()
                driver.set_page_load_timeout(self.timeout)
                driver.get(url)
                content = driver.page_source
                logger.info(f"Successfully fetched content using Selenium from {url}")
                return content
            except TimeoutException:
                logger.error(f"Selenium page load timed out for {url}")
                return None
            except WebDriverException as e:
                logger.error(f"Selenium WebDriver error for {url}: {e}")
                return None
            finally:
                if driver:
                    driver.quit()
        else:
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()  # Raise an exception for HTTP errors
                logger.info(f"Successfully fetched content using requests from {url}")
                return response.text
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch content from {url} using requests: {e}")
                return None

    def get_pdf_hash(self, url):
        """Fetches a PDF and returns its SHA256 hash."""
        logger.info(f"Fetching PDF from: {url} to calculate hash.")
        headers = {'User-Agent': self.user_agent}
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            hasher = hashlib.sha256()
            for chunk in response.iter_content(chunk_size=8192):
                hasher.update(chunk)
            
            logger.info(f"Successfully calculated PDF hash for {url}")
            return hasher.hexdigest()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch PDF from {url}: {e}")
            return None