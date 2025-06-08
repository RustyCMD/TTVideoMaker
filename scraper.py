# This file will contain the TikTok scraping logic using Selenium.

import os
import time
import requests
import subprocess # Added for yt-dlp
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, parse_qs

import tiktok_scraper
# If not, it might be tiktokscraper.TikTokScraper or similar

# Local imports
import utils

# Configuration
# TIKTOK_BASE_URL = "https://www.tiktok.com/" # Kept for reference
TRENDING_URL = "https://www.tiktok.com/foryou" # Or explore specific trending hashtags/pages
VIDEOS_DOWNLOAD_DIR = "videos"
EDITED_VIDEOS_DIR = "edited_videos" # Defined here for consistency if needed

# Ensure download directory exists
os.makedirs(VIDEOS_DOWNLOAD_DIR, exist_ok=True)
os.makedirs(EDITED_VIDEOS_DIR, exist_ok=True) # Ensure editor output dir also exists

def _log(message, level="INFO", log_queue=None):
    """Helper function to log to queue or print."""
    if log_queue:
        log_queue.put(("LOG", message, level))
    else:
        print(f"[{level}] {message}")

def setup_driver(log_queue=None):
    """Sets up and returns a Selenium Chrome WebDriver instance."""
    _log("Setting up Chrome WebDriver...", "DEBUG", log_queue)
    options = webdriver.ChromeOptions()
    # Add any desired options, e.g., headless mode, user agent
    # options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
    # Suppress console logs from WebDriver Manager and Selenium
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        _log("WebDriver setup successful.", "DEBUG", log_queue)
        return driver
    except Exception as e:
        _log(f"Error setting up WebDriver: {e}", "ERROR", log_queue)
        _log("Please ensure Google Chrome is installed and accessible.", "ERROR", log_queue)
        _log("You might also need to check your internet connection for WebDriverManager.", "ERROR", log_queue)
        return None

def get_video_id_from_url(url, log_queue=None):
    """Extracts a unique video ID from a TikTok video URL."""
    # Example URL: https://www.tiktok.com/@username/video/1234567890123456789
    # The last part of the path is usually the video ID.
    try:
        path_parts = urlparse(url).path.split('/')
        # Find the part that is a long number (video ID)
        for part in reversed(path_parts):
            if part.isdigit() and len(part) > 15: # TikTok IDs are typically long numbers
                return part
    except Exception as e:
        _log(f"Error extracting video ID from {url}: {e}", "ERROR", log_queue)
    return None

def get_video_links_from_tiktok(driver, hashtag, num_videos_to_find=10, scroll_pauses=5, scroll_time=3, log_queue=None):
    """
    Navigates to TikTok, scrolls to load videos, and extracts video links and IDs.
    Returns a list of tuples: (video_id, video_url)
    This is a basic implementation and will likely need refinement for TikTok's dynamic loading.
    """
    if not driver:
        _log("WebDriver not available for get_video_links_from_tiktok.", "ERROR", log_queue)
        return []

    if not hashtag:
        _log("Hashtag not provided to get_video_links_from_tiktok.", "ERROR", log_queue)
        return []

    target_url = f"https://www.tiktok.com/tag/{hashtag.strip()}"
    _log(f"Navigating to hashtag page: {target_url}...", "INFO", log_queue)
    if log_queue: log_queue.put(("STATUS_UPDATE", f"Navigating to tag: {hashtag}..."))
    
    try:
        driver.get(target_url)
    except Exception as e:
        _log(f"Error navigating to {target_url}: {e}", "ERROR", log_queue)
        return []

    _log(f"Please wait for page to load. Manually handle CAPTCHAs/pop-ups if they appear.", "INFO", log_queue)
    if log_queue: log_queue.put(("STATUS_UPDATE", "Waiting for TikTok page to load (handle popups/CAPTCHA if any)..."))

    # XPath for the container of videos. This might need adjustment for tag pages.
    # Common patterns: 'DivVideoFeed', 'DivChallengeLayoutContent', 'DivVideoList'
    feed_container_xpath = (
        "//div[contains(@class, 'DivVideoFeed')] | "
        "//div[contains(@class, 'DivChallengeLayoutContent')] | " # Often used on tag pages
        "//div[contains(@data-e2e, 'challenge-video-list')] | " # Another possibility for tag pages
        "//div[contains(@data-e2e, 'video-feed')] | "
        "//div[contains(@class, 'DivItemContainer')] | "
        "//div[starts-with(@class, 'DivVideoFeed')]")

    try:
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.XPATH, feed_container_xpath))
        )
        _log("Main video feed/list container detected on tag page.", "INFO", log_queue)
    except Exception as e:
        _log(f"Timeout or error finding main video feed container on tag page '{hashtag}'. Structure may have changed: {e}", "ERROR", log_queue)
        # Consider taking a screenshot here for debugging if it fails often
        # driver.save_screenshot(f"debug_tag_page_{hashtag}_load_failure.png")
        # _log(f"Saved screenshot: debug_tag_page_{hashtag}_load_failure.png", "DEBUG", log_queue)
        return []

    video_info_list = []
    found_video_ids = set()

    # XPath for individual video items/links. This is relatively generic.
    video_elements_xpath = "//div[contains(@data-e2e, 'video-item') or contains(@class, 'DivItemContainer') or (starts-with(@class, 'tiktok-') and contains(@class, 'DivItemContainer'))]//a[contains(@href,'/video/')]"

    for i in range(scroll_pauses):
        _log(f"Scroll attempt {i+1}/{scroll_pauses} for hashtag '{hashtag}'. Scrolling down...", "DEBUG", log_queue)
        if log_queue: log_queue.put(("STATUS_UPDATE", f"Scrolling page for #{hashtag} (attempt {i+1}/{scroll_pauses})..."))
        
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            _log(f"Waiting {scroll_time} seconds for videos to load...", "DEBUG", log_queue)
            time.sleep(scroll_time)
        except Exception as e_scroll:
            _log(f"Error during scrolling or sleep: {e_scroll}", "WARNING", log_queue)
            # Decide if we should break or continue if scrolling fails
            break

        try:
            video_elements = driver.find_elements(By.XPATH, video_elements_xpath)
        except Exception as e_find:
            _log(f"Error finding video elements with XPath: {e_find}", "ERROR", log_queue)
            video_elements = [] # Avoid crashing, proceed as if none found
            
        _log(f"Found {len(video_elements)} potential video link elements after scroll {i+1}.", "DEBUG", log_queue)

        for element in video_elements:
            try:
                video_url = element.get_attribute('href')
                if video_url and '/video/' in video_url:
                    video_id = get_video_id_from_url(video_url, log_queue)
                    if video_id and video_id not in found_video_ids:
                        if not utils.is_video_processed(video_id):
                            _log(f"Found new video: ID - {video_id}, URL - {video_url}", "INFO", log_queue)
                            video_info_list.append((video_id, video_url))
                            found_video_ids.add(video_id)
                            if len(video_info_list) >= num_videos_to_find:
                                break
                        else:
                            _log(f"Skipping already processed video ID (from file): {video_id}", "DEBUG", log_queue)
            except Exception as e:
                _log(f"Error processing a video element: {e}", "ERROR", log_queue)
        
        if len(video_info_list) >= num_videos_to_find:
            _log(f"Target number of {num_videos_to_find} new videos found for hashtag '{hashtag}'.", "INFO", log_queue)
            break
        _log(f"Collected {len(video_info_list)} new videos so far for hashtag '{hashtag}'...", "DEBUG", log_queue)

    if not video_info_list:
        _log(f"No new video links found for hashtag '{hashtag}'. Possible reasons:", "WARNING", log_queue)
        _log("  1. TikTok page structure changed (CSS/XPath needs update).", "WARNING", log_queue)
        _log("  2. No new videos on the page that haven't been processed.", "WARNING", log_queue)
        _log("  3. CAPTCHA or login required (manual intervention needed).", "WARNING", log_queue)
        _log("  4. All videos found were already processed or hashtag has no videos.", "WARNING", log_queue)

    return video_info_list[:num_videos_to_find]

def download_video(video_id, video_url, download_folder=VIDEOS_DOWNLOAD_DIR, log_queue=None):
    """Downloads a video from the given URL using yt-dlp if it hasn't been processed.
       Returns the path to the downloaded video, or None otherwise.
    """
    if utils.is_video_processed(video_id):
        _log(f"Video {video_id} already processed (checked again). Skipping download.", "INFO", log_queue)
        return None

    filepath = os.path.join(download_folder, f"{video_id}.mp4")
    os.makedirs(download_folder, exist_ok=True)
    process = None # Initialize process to None

    try:
        _log(f"Attempting to download video: {video_id} from {video_url} using yt-dlp...", "INFO", log_queue)
        if log_queue: log_queue.put(("STATUS_UPDATE", f"Downloading video {video_id}..."))

        command = [
            "yt-dlp", "--no-warnings", "--ignore-errors", "--retries", "3",
            "--fragment-retries", "3", "--no-playlist", "-o", filepath,
            video_url,
            "--socket-timeout", "30"
        ]
        
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creation_flags)
        stdout, stderr = process.communicate(timeout=120)

        if process.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            _log(f"Video {video_id} downloaded by yt-dlp. Verifying integrity with ffprobe...", "DEBUG", log_queue)
            
            # --- Add ffprobe verification step ---
            ffprobe_command = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", filepath]
            try:
                verify_process = subprocess.Popen(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creation_flags)
                ff_stdout, ff_stderr = verify_process.communicate(timeout=30)

                if verify_process.returncode == 0 and ff_stdout.strip(): # Check for codec name output
                    _log(f"Video {video_id} integrity verified by ffprobe. Codec: {ff_stdout.strip()}", "SUCCESS", log_queue)
                    return filepath
                else:
                    _log(f"ffprobe verification failed for {filepath}. Video might be corrupt.", "ERROR", log_queue)
                    _log(f"ffprobe RC: {verify_process.returncode}", "ERROR", log_queue)
                    _log(f"ffprobe stdout: {ff_stdout.strip()}", "DEBUG", log_queue)
                    _log(f"ffprobe stderr: {ff_stderr.strip()}", "ERROR", log_queue)
                    if os.path.exists(filepath):
                        try: os.remove(filepath)
                        except OSError as e_rem: _log(f"Error removing corrupted download file {filepath}: {e_rem}", "ERROR", log_queue)
                    return None
            except subprocess.TimeoutExpired:
                _log(f"ffprobe timed out verifying {filepath}. Assuming corrupt.", "ERROR", log_queue)
                if verify_process and verify_process.poll() is None: verify_process.kill()
                if os.path.exists(filepath):
                    try: os.remove(filepath)
                    except OSError as e_rem: _log(f"Error removing timed-out verification file {filepath}: {e_rem}", "ERROR", log_queue)
                return None
            except FileNotFoundError: # ffprobe not found
                _log("CRITICAL: ffprobe (part of FFmpeg) not found in PATH. Cannot verify video integrity.", "CRITICAL", log_queue)
                _log("Please ensure FFmpeg is installed and in PATH. The downloaded file will be kept but may be corrupt.", "WARNING", log_queue)
                return filepath # Return path, but it's unverified
            except Exception as e_ffprobe:
                _log(f"Error during ffprobe verification for {filepath}: {e_ffprobe}", "ERROR", log_queue)
                if os.path.exists(filepath):
                    try: os.remove(filepath)
                    except OSError as e_rem: _log(f"Error removing file after ffprobe error {filepath}: {e_rem}", "ERROR", log_queue)
                return None
            # --- End ffprobe verification step ---

        else:
            _log(f"Failed to download video {video_id}. yt-dlp RC: {process.returncode}", "ERROR", log_queue)
            _log(f"File path: {filepath}, Exists: {os.path.exists(filepath)}, Size: {os.path.getsize(filepath) if os.path.exists(filepath) else 'N/A'}", "DEBUG", log_queue)
            _log(f"yt-dlp stdout: {stdout.strip()}", "DEBUG", log_queue)
            _log(f"yt-dlp stderr: {stderr.strip()}", "ERROR", log_queue)
            if os.path.exists(filepath) and (os.path.getsize(filepath) == 0 or process.returncode != 0):
                try: os.remove(filepath)
                except OSError as e_rem: _log(f"Error removing problematic download file {filepath}: {e_rem}", "ERROR", log_queue)
            return None

    except subprocess.TimeoutExpired:
        _log(f"yt-dlp timed out downloading video {video_id}.", "ERROR", log_queue)
        if process and process.poll() is None: process.kill()
        # It's tricky to get stdout/stderr reliably after process.kill() before communicate was called
        # So we ensure communication happened before or this will hang
        # stdout, stderr = process.communicate() # This would hang if not already communicated
        _log(f"yt-dlp process killed due to timeout.", "DEBUG", log_queue) # Simplified logging here
        if os.path.exists(filepath):
            try: os.remove(filepath)
            except OSError as e_rem_tout: _log(f"Error removing timed-out download file {filepath}: {e_rem_tout}", "ERROR", log_queue)
        return None
    except FileNotFoundError: # yt-dlp not found
        _log("CRITICAL: yt-dlp command not found. Ensure yt-dlp is installed and in PATH.", "CRITICAL", log_queue)
        _log("Install with: pip install yt-dlp", "CRITICAL", log_queue)
        return None
    except Exception as e:
        _log(f"An unexpected error occurred downloading video {video_id}: {e}", "ERROR", log_queue)
        # Ensure process is not None before checking returncode
        rc = process.returncode if process else 'N/A'
        if os.path.exists(filepath):
             if not (os.path.getsize(filepath) > 0 and rc == 0) :
                try: os.remove(filepath)
                except OSError as e_rem_ex: _log(f"Error removing file {filepath} on exception: {e_rem_ex}", "ERROR", log_queue)
        return None

def get_video_id_from_metadata(video_data):
    """
    Extracts a unique video ID from tiktok-scraper metadata.
    """
    if not video_data:
        return None
    
    possible_id_keys = ['id', 'itemId', 'video_id', 'itemInfos.id'] # itemInfos.id for some structures
    for key in possible_id_keys:
        if '.' in key: # Handle nested keys like 'itemInfos.id'
            parts = key.split('.')
            value = video_data
            try:
                for part in parts:
                    value = value[part]
                if value: return str(value)
            except (KeyError, TypeError):
                continue
        elif isinstance(video_data, dict) and video_data.get(key):
            return str(video_data[key])
    
    # Fallback for other potential structures if necessary
    if isinstance(video_data, dict) and video_data.get('video', {}).get('id'):
         return str(video_data['video']['id'])

    _log(f"Could not extract video ID from metadata structure: {str(video_data)[:200]}...", "WARNING")
    return None

def verify_downloaded_video(filepath, video_id, log_queue=None):
    """
    Verifies the integrity of a downloaded video using ffprobe.
    Returns True if valid, False otherwise. Deletes invalid file.
    """
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        _log(f"File {filepath} for video {video_id} is missing or empty before ffprobe check.", "ERROR", log_queue)
        if os.path.exists(filepath): # Remove if zero size
            try: os.remove(filepath)
            except OSError: pass
        return False

    _log(f"Verifying integrity of {filepath} for video {video_id} with ffprobe...", "DEBUG", log_queue)
    ffprobe_command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0", 
        "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", filepath
    ]
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    verify_process = None
    try:
        verify_process = subprocess.Popen(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creation_flags)
        ff_stdout, ff_stderr = verify_process.communicate(timeout=30)

        if verify_process.returncode == 0 and ff_stdout.strip():
            _log(f"Video {video_id} integrity verified by ffprobe. Codec: {ff_stdout.strip()}", "SUCCESS", log_queue)
            return True
        else:
            _log(f"ffprobe verification failed for {filepath} (ID: {video_id}). Video might be corrupt.", "ERROR", log_queue)
            _log(f"ffprobe RC: {verify_process.returncode}, STDOUT: '{ff_stdout.strip()}', STDERR: '{ff_stderr.strip()}'", "DEBUG", log_queue)
            if os.path.exists(filepath):
                try: os.remove(filepath)
                except OSError as e_rem: _log(f"Error removing corrupted download file {filepath}: {e_rem}", "ERROR", log_queue)
            return False
    except subprocess.TimeoutExpired:
        _log(f"ffprobe timed out verifying {filepath} (ID: {video_id}). Assuming corrupt.", "ERROR", log_queue)
        if verify_process and verify_process.poll() is None: verify_process.kill()
        if os.path.exists(filepath): 
            try: os.remove(filepath)
            except OSError as e_rem: _log(f"Error removing file after ffprobe timeout {filepath}: {e_rem}", "ERROR", log_queue)
        return False
    except FileNotFoundError:
        _log("CRITICAL: ffprobe (part of FFmpeg) not found in PATH. Cannot verify video integrity.", "CRITICAL", log_queue)
        _log("Please ensure FFmpeg is installed and in PATH. Downloaded files will be kept but may be corrupt.", "WARNING", log_queue)
        return True # Keep file but warn, editing might fail
    except Exception as e_ffprobe:
        _log(f"Error during ffprobe verification for {filepath} (ID: {video_id}): {e_ffprobe}", "ERROR", log_queue)
        if os.path.exists(filepath): 
            try: os.remove(filepath)
            except OSError as e_rem: _log(f"Error removing file after ffprobe error {filepath}: {e_rem}", "ERROR", log_queue)
        return False

def scrape_and_download_videos_by_hashtag(hashtag: str, num_videos_to_find: int, log_queue=None):
    """
    Orchestrates scraping video links with Selenium and downloading with yt-dlp.
    Returns a list of dictionaries with info about downloaded videos.
    """
    _log(f"Initializing scraping process for hashtag: #{hashtag}", "INFO", log_queue)
    processed_video_details = []
    driver = None  # Initialize driver to None

    try:
        driver = setup_driver(log_queue=log_queue)
        if not driver:
            _log("Failed to setup WebDriver. Aborting scrape.", "CRITICAL", log_queue)
            return []

        # Step 1: Get video links using Selenium
        video_links_info = get_video_links_from_tiktok(
            driver=driver,
            hashtag=hashtag,
            num_videos_to_find=num_videos_to_find,
            log_queue=log_queue
        )

        if not video_links_info:
            _log(f"No new video links found for hashtag '{hashtag}'.", "WARNING", log_queue)
            return []
        
        total_to_download = len(video_links_info)
        _log(f"Found {total_to_download} new video(s). Starting download process...", "INFO", log_queue)

        # Step 2: Download each video using yt-dlp
        for i, (video_id, video_url) in enumerate(video_links_info):
            if log_queue:
                log_queue.put(("STATUS_UPDATE", f"Downloading video {i+1}/{total_to_download}..."))
            
            downloaded_filepath = download_video(
                video_id=video_id,
                video_url=video_url,
                log_queue=log_queue
            )

            if downloaded_filepath:
                _log(f"Successfully downloaded video {video_id} to {downloaded_filepath}", "SUCCESS", log_queue)
                processed_video_details.append({'id': video_id, 'filepath': downloaded_filepath})
            else:
                _log(f"Failed to download video {video_id}. It may have been skipped or an error occurred.", "ERROR", log_queue)
        
        return processed_video_details

    except Exception as e:
        _log(f"An unexpected error occurred during the main scraping/downloading process: {e}", "CRITICAL", log_queue)
        import traceback
        _log(traceback.format_exc(), "DEBUG", log_queue)
        return processed_video_details # Return any videos that were processed before the error
    finally:
        if driver:
            _log("Closing WebDriver.", "DEBUG", log_queue)
            try:
                driver.quit()
            except Exception as e_quit:
                _log(f"Error while quitting WebDriver: {e_quit}", "WARNING", log_queue)

if __name__ == '__main__':
    print("Starting TikTok Scraper Test (using tiktok-scraper library)...")
    test_hashtag = "funnycat" 
    num_to_find = 1

    # Setup for test processed_videos.txt
    test_data_dir = "data"
    os.makedirs(test_data_dir, exist_ok=True)
    
    # Store original utils.PROCESSED_VIDEOS_FILE path and temporarily override for test
    original_processed_file_path = utils.PROCESSED_VIDEOS_FILE
    utils.PROCESSED_VIDEOS_FILE = os.path.join(test_data_dir, "test_processed_scraper.txt")
    if os.path.exists(utils.PROCESSED_VIDEOS_FILE):
        try:
            os.remove(utils.PROCESSED_VIDEOS_FILE)
        except OSError as e_rem_main_test:
             print(f"Error removing existing test processed file: {e_rem_main_test}")

    # Example: Add a dummy ID to test filtering
    # utils.add_processed_video("dummy_id_12345") 
    # print(f"Current processed (for test): {utils.get_processed_videos()}")
    
    print(f"Testing with hashtag: #{test_hashtag}, looking for {num_to_find} new videos.")
    
    found_videos = scrape_and_download_videos_by_hashtag(
        hashtag=test_hashtag,
        num_videos_to_find=num_to_find,
        log_queue=None # No GUI queue for this direct test
    )

    if found_videos:
        print(f"\nFound {len(found_videos)} NEW video(s) for hashtag #{test_hashtag}:")
        for video_info in found_videos:
            video_id = video_info['id']
            filepath = video_info['filepath']
            print(f"  ID: {video_id}, Path: {filepath}")
            if os.path.exists(filepath):
                print(f"    -> File exists at: {filepath}, Size: {os.path.getsize(filepath)} bytes")
                # Optional: Clean up test downloaded files
                # try:
                #     os.remove(filepath)
                #     print(f"    -> Test file {filepath} removed.")
                # except OSError as e_rem_test_dl:
                #     print(f"    -> Error removing test downloaded file {filepath}: {e_rem_test_dl}")
            else:
                print(f"    -> ERROR: File {filepath} for video ID {video_id} was expected but not found post-scraping!")
    else:
        print(f"No new, valid videos found for hashtag #{test_hashtag} during the command-line test.")

    # Clean up test processed_videos.txt and restore original path in utils
    if os.path.exists(utils.PROCESSED_VIDEOS_FILE):
        try:
            os.remove(utils.PROCESSED_VIDEOS_FILE)
        except OSError as e_rem_main_test_end:
            print(f"Error removing test processed file at end: {e_rem_main_test_end}")
    utils.PROCESSED_VIDEOS_FILE = original_processed_file_path # Reset to default

    print("\nTikTok Scraper (tiktok-scraper library) Test Finished.")