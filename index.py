"""Module for getting all links and starting the download process."""

import os
import downloader


def start():
    """Main function to start the application"""
    download_dir = "downloads"
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    default_wait_time = 60
    print("Welcome to Repack Downloader")
    wait_time_input = input(
        "Please enter wait time in seconds: "
        "\n This is for waiting between each download to avoid bot detection."
        " \n Default is 60. Press enter for default waiting time."
    )
    if wait_time_input:
        wait_time = int(wait_time_input)
    else:
        wait_time = default_wait_time

    url = input("Enter url: ")

    # Fetch all links from the provided URL
    links = downloader.get_all_links(url=url)
    if links:
        print("All links fetched successfully. \n Starting Download...")
        downloader.start_download(
            links=links, download_dir=download_dir, wait_time=wait_time
        )
    else:
        print("Fetching links Unsuccessful. ")


if __name__ == "__main__":
    start()
