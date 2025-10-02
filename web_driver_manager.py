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
        # Stable headless flags for CI/containers/Linux servers
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--window-size=1280,720")
        # Allow overriding Chrome binary location via env var if needed
        # (useful in minimal containers)
        import os as _os
        if _os.getenv("CHROME_BIN"):
            chrome_options.binary_location = _os.getenv("CHROME_BIN")
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the WebDriver."""
        if self.driver:
            self.driver.quit()
