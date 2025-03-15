"""Module for tracking time"""

import re
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


def initiate_dirver(url: str, delay: int = 1) -> webdriver:
    """_summary_

    Args:
        url (str): _description_
        delay (int, optional): load time for web page. Defaults to 2.

    Returns:
        WebDriver: _description_
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    # print("Running the driver please wait..")
    driver.get(url)
    time.sleep(delay)
    return driver


def get_all_links(url: str) -> list[str]:
    """_summary_

    Args:
        url (str): url of fitgirl repack fuckingfast pastebin

    Returns:
        list[str]: list containing string of links
    """
    driver = initiate_dirver(url)
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, "html.parser")
    driver.quit()

    div_plaintext = soup.find("div", id="plaintext")
    if div_plaintext is None:
        print(
            "Cannot find the download links.\n"
            "The url might be incorrect.\n"
            "Please enter new url and try again."
        )
        new_url = input("Enter new url :  \n")
        return get_all_links(new_url)

    ul = div_plaintext.find("ul")
    if ul is None:
        print("No <ul> element found within the div.")
        return []

    links: list[str] = []
    for li in ul.find_all("li"):
        a_tag = li.find("a")
        if a_tag and "href" in a_tag.attrs:
            links.append(a_tag["href"])
    return links


def get_direct_download_links(url: str) -> str:
    """Get direct downaload links

    Args:
        url (str): url link to download page

    Returns:
        str: direct downaload link
    """

    js_code = get_js_code(url)
    download_link = extract_url(js_code)
    return download_link


def extract_url(js_code: str) -> str:
    """extract url from the js code

    Args:
        js_code (str): strings of js code

    Returns:
        str: direct download url
    """
    pattern = r'window\.open\("([^"]+)"'
    url_match = re.search(pattern, js_code)
    if not url_match:
        raise ValueError("Could not find the download url in script")
    download_url = url_match.group(1)
    return download_url


def get_js_code(url: str) -> str:
    """extract scripts

    Args:
        url (str): _description_

    Returns:
        str: _description_
    """
    driver = initiate_dirver(url)
    script_elements = driver.find_elements(By.TAG_NAME, "script")
    js_code = ""
    for script in script_elements:
        js_code += script.get_attribute("innerHTML")
    driver.quit()
    return js_code


# Function to sanitize filenames
def sanitize_filename(filename):
    """
    Sanitizes a filename by removing invalid characters.

    :param filename: The original filename.
    :return: A sanitized filename.
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Trim leading/trailing spaces and dots
    sanitized = sanitized.strip(". ")
    return sanitized


def download_file(url, filename, timeout=(60, 1200), max_retries=6):
    """
    Downloads a file from a URL and saves it to the specified filename.
    Shows download progress in the console.

    :param url: The direct download URL of the file.
    :param filename: The path where the file will be saved.
    :param timeout: Timeout for the request in seconds (connect, read).
    :param max_retries: Maximum number of retries if the download fails.
    """
    retries = 0

    while retries < max_retries:
        try:
            # Send a GET request to the URL with streaming enabled
            with requests.get(url, stream=True, timeout=timeout) as r:
                r.raise_for_status()  # Raise an error for bad status codes
                total_size = int(
                    r.headers.get("content-length", 0)
                )  # Total file size in bytes
                downloaded_size = 0  # Track the number of bytes downloaded
                chunk_size = (
                    1048576  # 1 MB chunks (optimized for high-speed connections)
                )

                # Open the file in binary write mode
                with open(filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        f.write(chunk)  # Write the chunk to the file
                        downloaded_size += len(chunk)  # Update the downloaded size
                        # Calculate and display the download progress
                        progress = (downloaded_size / total_size) * 100
                        print(
                            f"Downloading {os.path.basename(filename)}: {progress:.2f}% complete",
                            end="\r",
                        )
                print(f"\nFinished downloading {os.path.basename(filename)}.")
                return True

        except requests.exceptions.RequestException as e:
            print(f"Request failed for {os.path.basename(filename)}: {e}")
        except IOError as e:
            print(f"File I/O error for {os.path.basename(filename)}: {e}")
        except Exception as e:
            print(f"Unexpected error for {os.path.basename(filename)}: {e}")

        # Delete the partially downloaded file if it exists
        if os.path.exists(filename):
            print(f"Deleting partially downloaded file: {os.path.basename(filename)}")
            os.remove(filename)

        # Increment retry count
        retries += 1
        if retries < max_retries:
            print(
                f"Retrying download for {os.path.basename(filename)} (attempt {retries + 1}/{max_retries})..."
            )
        else:
            print(f"Max retries reached for {os.path.basename(filename)}. Skipping...")
            return False


def start_download(links: list[str], download_dir, wait_time=60) -> None:
    """Start the download

    Args:
        links (list[str]): list of download links
        download_dir (_type_): download directory
        wait_time (int, optional): wait time. Defaults to 60.
    """
    failed_downloads = download_all(
        links=links, download_dir=download_dir, wait_time=wait_time
    )
    total_failed = len(failed_downloads)
    if total_failed < 0:
        print(f"There are {total_failed} failed download.")
        user_input = input("Do you want to try downloading them again? (Y/n)")
        if user_input == "Y" or user_input == "y" or user_input is None:
            start_download(
                links=failed_downloads,
                download_dir=download_dir,
                wait_time=wait_time,
            )
        else:
            print("All Download Completed Successfully")


def download_all(links: list[str], download_dir: str, wait_time=60) -> list:
    """Start Downloading all files

    Args:
        links (list[str]): List of direct download links
        download_dir (str): directory to save the downloaded files
        wait_time (int, optional): wait time between downloads to avoid bot detection. Defaults to 60.

    Returns:
        list: list of failed download links
    """
    failed_downloads = []
    for link in links:
        download_link = get_direct_download_links(link)
        if download_link:
            # Sanitize the filename
            filename = sanitize_filename(link.split("#")[-1])
            filepath = os.path.join(download_dir, filename)

            if os.path.exists(filepath):
                print(f"File {filename} already exits. Skipping...")
                continue

            print(f"Starting download for {filename}...")
            try:
                result = download_file(download_link, filepath)
                if result is not True:
                    failed_downloads.append(download_link)

            except Exception as e:
                print(f"Failed to download {filename}: {e}")
        else:
            print(f"Couldn't find the download link for {link}.")

        print("Waiting 2 minutes until next download to avoid bot detection...")
        # Wait for 2 minutes before the next download
        time.sleep(wait_time)
    return failed_downloads
