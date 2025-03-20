"""Module for downloading files and handling web interactions"""

import os
import re
import time
import requests
from selenium.webdriver.common.by import By
from link_extractor import LinkExtractor
from web_driver_manager import WebDriverManager


class DownloadManager:
    """Manages the download process, including retries and progress tracking."""

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)

    def get_wait_time(self) -> int:
        """Prompt the user for wait time between downloads."""
        default_wait_time = 60
        wait_time_input = input(
            "Please enter wait time in seconds:\n"
            "This is for waiting between each download to avoid bot detection.\n"
            f"Default is {default_wait_time}. Press Enter for default waiting time: "
        )
        return int(wait_time_input) if wait_time_input else default_wait_time

    def process_url(self, url: str, wait_time: int) -> None:
        """Process the URL, fetch links, and start downloading."""
        links = LinkExtractor(url).get_all_links()
        if links:
            print("All links fetched successfully.\nStarting Download...")
            self.download_all(links, wait_time)
        else:
            print("Fetching links unsuccessful.")

    def download_all(self, links: list[str], wait_time: int) -> None:
        """Download all files from the provided links."""
        failed_downloads = []
        for link in links:
            try:
                download_link = self.get_direct_download_link(link)
                if not download_link:
                    print(f"Couldn't find the download link for {link}.")
                    continue

                filename = self.sanitize_filename(link.split("#")[-1])
                filepath = os.path.join(self.download_dir, filename)

                if os.path.exists(filepath):
                    print(f"File {filename} already exists. Skipping...")
                    continue

                print(f"Starting download for {filename}...")
                if not self.download_file(download_link, filepath):
                    failed_downloads.append(link)

                print(f"Waiting {wait_time} seconds until the next download...")
                time.sleep(wait_time)
            except (requests.RequestException, ValueError) as e:
                print(f"Failed to process {link}: {e}")
                failed_downloads.append(link)

        if failed_downloads:
            print(f"There are {len(failed_downloads)} failed downloads.")
            retry = (
                input("Do you want to try downloading them again? (Y/n): ")
                .strip()
                .lower()
            )
            if retry in ("y", ""):
                self.download_all(failed_downloads, wait_time)
        else:
            print("All downloads completed successfully.")

    def get_direct_download_link(self, url: str) -> str:
        """Extract the direct download link from the provided URL."""
        js_code = self.get_js_code(url)
        return self.extract_url(js_code)

    def get_js_code(self, url: str) -> str:
        """Extract JavaScript code from the provided URL."""
        with WebDriverManager() as driver:
            driver.get(url)
            script_elements = driver.find_elements(By.TAG_NAME, "script")
            return "".join(
                script.get_attribute("innerHTML") for script in script_elements
            )

    @staticmethod
    def extract_url(js_code: str) -> str:
        """Extract the URL from JavaScript code."""
        pattern = r'window\.open\("([^"]+)"'
        url_match = re.search(pattern, js_code)
        if not url_match:
            raise ValueError("Could not find the download URL in the script.")
        return url_match.group(1)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize a filename by removing invalid characters."""
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        return sanitized.strip(". ")

    @staticmethod
    def download_file(
        url: str,
        filename: str,
        timeout: tuple[int, int] = (60, 1200),
        max_retries: int = 6,
    ) -> bool:
        """Download a file from a URL with retries and progress tracking."""
        for retry in range(max_retries):
            try:
                with requests.get(url, stream=True, timeout=timeout) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get("content-length", 0))
                    downloaded_size = 0
                    chunk_size = 1048576  # 1 MB

                    with open(filename, "wb") as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            progress = (downloaded_size / total_size) * 100
                            print(
                                f"Downloading {os.path.basename(filename)}: {progress:.2f}% complete",
                                end="\r",
                            )
                    print(f"\nFinished downloading {os.path.basename(filename)}.")
                    return True
            except (requests.RequestException, OSError) as e:
                print(
                    f"Error downloading {os.path.basename(filename)} (attempt {retry + 1}/{max_retries}): {e}"
                )
                if os.path.exists(filename):
                    os.remove(filename)
        return False
