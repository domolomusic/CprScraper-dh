import requests
import logging
import hashlib
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup # Although not directly used for content fetching, good for future parsing

logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.monitoring_settings = self.config_loader.get_setting('monitoring_settings')
        self.user_agent = self.monitoring_settings.get('user_agent', 'PayrollMonitor/1.0 (Government Forms Monitoring)')
        self.timeout = self.monitoring_settings.get('timeout_seconds', 30)
        logger.info("WebScraper initialized.")

    def _get_chrome_driver(self):
        """Initializes and returns a headless Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"user-agent={self.user_agent}")
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            return None

    def fetch_content(self, url, use_js_rendering=False):
        """
        Fetches content from a given URL.
        If use_js_rendering is True, uses Selenium for JavaScript-heavy pages.
        Otherwise, uses requests for static content.
        """
        logger.info(f"Fetching content from: {url} (JS rendering: {use_js_rendering})")
        try:
            if use_js_rendering:
                driver = self._get_chrome_driver()
                if not driver:
                    return None
                try:
                    driver.get(url)
                    # You might need to add explicit waits here for dynamic content to load
                    # from selenium.webdriver.support.ui import WebDriverWait
                    # from selenium.webdriver.support import expected_conditions as EC
                    # from selenium.webdriver.common.by import By
                    # WebDriverWait(driver, self.timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    return driver.page_source
                finally:
                    driver.quit()
            else:
                headers = {'User-Agent': self.user_agent}
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return None

    def get_pdf_hash(self, pdf_url):
        """
        Downloads a PDF and returns its SHA256 hash.
        """
        logger.info(f"Fetching PDF from: {pdf_url} to calculate hash.")
        try:
            headers = {'User-Agent': self.user_agent}
            response = requests.get(pdf_url, headers=headers, timeout=self.timeout, stream=True)
            response.raise_for_status()

            hasher = hashlib.sha256()
            for chunk in response.iter_content(chunk_size=8192):
                hasher.update(chunk)
            
            pdf_hash = hasher.hexdigest()
            logger.info(f"Successfully calculated PDF hash for {pdf_url}: {pdf_hash[:10]}...")
            return pdf_hash
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download PDF from {pdf_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing PDF from {pdf_url}: {e}")
            return None