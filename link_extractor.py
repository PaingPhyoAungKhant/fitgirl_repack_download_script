"""Module for downloading files and handling web interactions"""

import time
from typing import List
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

        uls: List = div_plaintext.find_all("ul")
        if not uls:
            print("No <ul> element found within the div.")
            return []

        links: list[str] = []
        for ul in uls:
            for li in ul.find_all("li"):
                a = li.find("a")
                if a and "href" in a.attrs:
                    href = a["href"].strip()
                    if href and href.startswith("http"):
                        links.append(href)
        # De-duplicate while preserving order
        seen = set()
        unique_links: list[str] = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        return unique_links
