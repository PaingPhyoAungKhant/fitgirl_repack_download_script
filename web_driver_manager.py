"""Module for downloading files and handling web interactions"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class WebDriverManager:
    """Manages the lifecycle of a Selenium WebDriver."""

    def __init__(self):
        self.driver = None

    def __enter__(self):
        """Initialize and return a headless Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the WebDriver."""
        if self.driver:
            self.driver.quit()
