"""Module for downloading files and handling web interactions"""

import os
import re
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from selenium.webdriver.common.by import By
from link_extractor import LinkExtractor
from web_driver_manager import WebDriverManager


class DownloadManager:
    """Manages the download process, including retries and progress tracking."""

    def __init__(self, download_dir: str = "downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        # Create a reusable HTTP session with connection pooling and retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            }
        )
        retry_cfg = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["HEAD", "GET", "OPTIONS"]),
        )
        adapter = HTTPAdapter(max_retries=retry_cfg, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

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
                if not self.download_file(download_link, filepath, session=self.session):
                    failed_downloads.append(link)

                # Add small jitter to avoid detectable fixed timing
                jittered_wait = max(0, wait_time * random.uniform(0.8, 1.2))
                print(f"Waiting {jittered_wait:.1f} seconds until the next download...")
                time.sleep(jittered_wait)
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
        """Extract the URL from JavaScript code.

        Supports patterns like:
        - window.open('URL')
        - window.open("URL", "_blank")
        - location.assign('URL') / location.href = 'URL'
        """
        patterns = [
            r"window\\.open\(\s*['\"]([^'\"]+)['\"]",
            r"location\\.(?:assign|replace)\(\s*['\"]([^'\"]+)['\"]",
            r"location\\.href\s*=\s*['\"]([^'\"]+)['\"]",
        ]
        for pattern in patterns:
            url_match = re.search(pattern, js_code)
            if url_match:
                return url_match.group(1)
        raise ValueError("Could not find the download URL in the script.")

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
        session: requests.Session | None = None,
    ) -> bool:
        """Download a file from a URL with retries, resume support, and progress tracking.

        The function writes to a temporary file with the suffix ".part" and
        atomically renames it to the final filename once the download completes.
        On failures, the partial file is preserved so subsequent retries can
        resume using HTTP Range requests.
        """
        temp_filename = f"{filename}.part"
        chunk_size = 1048576  # 1 MB

        sess = session or requests.Session()
        for retry in range(max_retries):
            try:
                existing_size = os.path.getsize(temp_filename) if os.path.exists(temp_filename) else 0
                headers = {}
                if existing_size > 0:
                    headers["Range"] = f"bytes={existing_size}-"

                with sess.get(url, stream=True, timeout=timeout, headers=headers) as response:
                    # If server does not honor Range and we already had bytes, start fresh
                    if existing_size > 0 and response.status_code == 200:
                        # Remove the partial and retry immediately from scratch
                        try:
                            os.remove(temp_filename)
                        except OSError:
                            pass
                        existing_size = 0
                        # Reissue request without Range in the same retry loop
                        with sess.get(url, stream=True, timeout=timeout) as response_no_range:
                            response_no_range.raise_for_status()
                            total_from_headers = response_no_range.headers.get("content-length")
                            total_size = int(total_from_headers) if total_from_headers and total_from_headers.isdigit() else 0
                            downloaded_size = 0
                            with open(temp_filename, "wb") as f:
                                for chunk in response_no_range.iter_content(chunk_size=chunk_size):
                                    if not chunk:
                                        continue
                                    f.write(chunk)
                                    downloaded_size += len(chunk)
                                    if total_size:
                                        progress = ((downloaded_size) / total_size) * 100
                                        print(
                                            f"Downloading {os.path.basename(filename)}: {progress:.2f}% complete",
                                            end="\r",
                                        )
                        os.replace(temp_filename, filename)
                        print(f"\nFinished downloading {os.path.basename(filename)}.")
                        return True

                    response.raise_for_status()

                    # Determine total size for progress
                    total_size = 0
                    content_range = response.headers.get("content-range")
                    if content_range and "/" in content_range:
                        # Format: bytes start-end/total
                        try:
                            total_size = int(content_range.split("/")[-1])
                        except ValueError:
                            total_size = 0
                    elif response.headers.get("content-length"):
                        try:
                            total_size = int(response.headers.get("content-length", "0")) + existing_size
                        except ValueError:
                            total_size = 0

                    mode = "ab" if existing_size > 0 and response.status_code in (206, 416) else "wb"
                    downloaded_size = existing_size

                    with open(temp_filename, mode) as f:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if not chunk:
                                continue
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if total_size:
                                progress = (downloaded_size / total_size) * 100
                                print(
                                    f"Downloading {os.path.basename(filename)}: {progress:.2f}% complete",
                                    end="\r",
                                )

                    # If we know total size and reached/exceeded it, finalize; otherwise, assume complete
                    if not total_size or downloaded_size >= total_size:
                        os.replace(temp_filename, filename)
                        print(f"\nFinished downloading {os.path.basename(filename)}.")
                        return True

                    # If we are here and haven't completed, we'll retry and resume
                    raise requests.RequestException("Connection ended before completing the file")

            except (requests.RequestException, OSError) as e:
                print(
                    f"Error downloading {os.path.basename(filename)} (attempt {retry + 1}/{max_retries}): {e}"
                )
                # Exponential backoff with jitter before next retry
                if retry + 1 < max_retries:
                    sleep_s = min(60.0, (2 ** retry) + random.uniform(0, 1))
                    print(f"Retrying in {sleep_s:.1f}s...")
                    time.sleep(sleep_s)
                # Preserve partial file for resume on next attempt
                continue

        return False
