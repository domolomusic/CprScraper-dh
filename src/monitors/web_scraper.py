import logging
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WebScraper:
    def __init__(self, user_agent="PayrollMonitor/1.0 (Government Forms Monitoring)", timeout=30):
        self.user_agent = user_agent
        self.timeout = timeout
        self.headers = {'User-Agent': self.user_agent}
        logging.info("WebScraper initialized.")

    def _fetch_with_requests(self, url):
        """Fetches content using the requests library for static pages."""
        try:
            logging.info(f"Fetching static content from: {url}")
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
            logging.info(f"Successfully fetched static content from: {url}")
            return response.text
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching static content from {url}: {e}")
            return None

    def _fetch_with_selenium(self, url):
        """Fetches content using Selenium for JavaScript-rendered pages."""
        logging.info(f"Fetching dynamic content from: {url} using Selenium.")
        options = Options()
        options.add_argument("--headless")  # Run in headless mode (no UI)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={self.user_agent}")
        
        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(self.timeout)
            driver.get(url)
            logging.info(f"Successfully fetched dynamic content from: {url}")
            return driver.page_source
        except TimeoutException:
            logging.error(f"Selenium page load timed out for {url}")
            return None
        except WebDriverException as e:
            logging.error(f"Selenium WebDriver error for {url}: {e}")
            return None
        finally:
            if driver:
                driver.quit()

    def fetch_page(self, url, use_selenium=False):
        """
        Public method to fetch page content.
        Args:
            url (str): The URL to fetch.
            use_selenium (bool): If True, use Selenium for dynamic content.
                                 Otherwise, use requests for static content.
        Returns:
            str: The page content as a string, or None if an error occurred.
        """
        if use_selenium:
            return self._fetch_with_selenium(url)
        else:
            return self._fetch_with_requests(url)

if __name__ == '__main__':
    # Example Usage (for testing purposes)
    scraper = WebScraper()

    # Test with a static page
    print("\n--- Testing static page fetch ---")
    static_url = "https://www.example.com"
    static_content = scraper.fetch_page(static_url)
    if static_content:
        print(f"Fetched {len(static_content)} characters from {static_url[:50]}...")
    else:
        print(f"Failed to fetch {static_url}")

    # Test with a dynamic page (requires a running Chrome/Chromium browser and webdriver)
    # Note: This might take a moment as it downloads the webdriver if not present.
    print("\n--- Testing dynamic page fetch (Selenium) ---")
    dynamic_url = "https://www.google.com" # A simple dynamic page
    dynamic_content = scraper.fetch_page(dynamic_url, use_selenium=True)
    if dynamic_content:
        print(f"Fetched {len(dynamic_content)} characters from {dynamic_url[:50]}...")
    else:
        print(f"Failed to fetch {dynamic_url}")