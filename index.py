"""Module for starting the download process"""

from download_manager import DownloadManager


def main():
    """Main function to start the application."""
    print("Welcome to Repack Downloader")

    # Initialize the DownloadManager
    download_manager = DownloadManager(download_dir="downloads")

    # Get user input for wait time and URL
    wait_time = download_manager.get_wait_time()
    url = input("Enter URL: ")

    # Fetch links and start downloading
    download_manager.process_url(url, wait_time)


if __name__ == "__main__":
    main()
