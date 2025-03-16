"""Module for downloading files and handling web interactions"""

import time
from bs4 import BeautifulSoup
from web_driver_manager import WebDriverManager


class LinkExtractor:
    """Extracts download links from a given URL."""

    def __init__(self, url: str):
        self.url = url

    def get_all_links(self) -> list[str]:
        """Fetch all download links from the provided URL."""
        with WebDriverManager() as driver:
            driver.get(self.url)
            time.sleep(1)  # Allow page to load
            soup = BeautifulSoup(driver.page_source, "html.parser")

        div_plaintext = soup.find("div", id="plaintext")
        if not div_plaintext:
            print(
                "Cannot find the download links.\n"
                "The URL might be incorrect.\n"
                "Please enter a new URL and try again."
            )
            new_url = input("Enter new URL: ")
            return LinkExtractor(new_url).get_all_links()

        ul = div_plaintext.find("ul")
        if not ul:
            print("No <ul> element found within the div.")
            return []

        return [
            a["href"]
            for li in ul.find_all("li")
            if (a := li.find("a")) and "href" in a.attrs
        ]
