# TTVideoMaker 🎬

TTVideoMaker is a desktop application designed to help you discover, download, and apply basic edits to TikTok videos based on hashtags. It features a user-friendly interface and automates the process of fetching new content, making it easier to curate videos for your needs.

## ✨ Features

*   **Graphical User Interface (GUI):** Easy-to-use interface built with CustomTkinter.
*   **Hashtag-Based Scraping:** Enter a TikTok hashtag to find relevant videos.
*   **Specify Video Count:** Choose how many new videos you want to process.
*   **Avoids Duplicates:** Keeps track of processed videos (`data/processed_videos.txt`) to prevent re-downloading and re-editing.
*   **Video Downloading:** Uses `yt-dlp` to download videos from TikTok.
*   **Download Verification:** Utilizes `ffprobe` to check the integrity of downloaded videos.
*   **Video Editing:** Leverages FFmpeg for basic video edits:
    *   **Mirroring:** Horizontally flips videos.
    *   **Cropping:** Applies a percentage-based crop from all sides.
*   **Real-time Logging:** View the progress and status of operations directly in the GUI.
*   **Progress Bar & Status Updates:** Stay informed about the current task.
*   **Asynchronous Operations:** Scraping and editing tasks run in a separate thread to keep the GUI responsive.
*   **Error Handling:** Provides feedback on issues encountered during the process.

## ⚠️ Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Python 3.x:** Download from [python.org](https://www.python.org/downloads/).
2.  **Google Chrome:** The application uses Selenium to interact with TikTok, which requires Chrome. Download from [google.com/chrome](https://www.google.com/chrome/).
3.  **FFmpeg (and ffprobe):** Essential for video editing and verification.
    *   Download from [ffmpeg.org](https://ffmpeg.org/download.html).
    *   **Crucial:** Add the `bin` directory of your FFmpeg installation (containing `ffmpeg.exe` and `ffprobe.exe`) to your system's PATH environment variable.
4.  **yt-dlp:** A powerful command-line tool for downloading videos.
    *   Installation instructions can be found on the [yt-dlp GitHub page](https://github.com/yt-dlp/yt-dlp#installation). Ensure `yt-dlp` (or `yt-dlp.exe`) is accessible from your command line/terminal (i.e., in your system's PATH).

## 🛠️ Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/TTVideoMaker.git
    cd TTVideoMaker
    ```
    *(Replace `https://github.com/your-username/TTVideoMaker.git` with the actual URL of your repository if applicable, or instruct users to download the ZIP if not using Git.)*

2.  **Install Python Dependencies:**
    It's highly recommended to use a virtual environment:
    ```bash
    python -m venv venv
    ```
    Activate the virtual environment:
    *   Windows: `.\venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`

    Then, install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
    This will install `customtkinter`, `selenium`, `webdriver-manager`, and `tiktok-scraper`. While `yt-dlp` is listed, ensure it's also globally available as a command-line tool (see Prerequisites).

3.  **Verify Prerequisites:** Double-check that Google Chrome, FFmpeg (with `ffmpeg` and `ffprobe` in PATH), and `yt-dlp` (in PATH) are correctly set up.

## 🚀 Usage

1.  **Run the Application:**
    Execute the `start.bat` script (on Windows) or run `main.py` directly:
    ```bash
    python main.py
    ```
    Alternatively, on Windows, you can simply double-click `start.bat`.

2.  **Using the GUI:**
    *   **Enter Hashtag:** In the "Hashtag" field, type the TikTok hashtag you're interested in (e.g., `funnycats`, `travelvlog`) **without** the `#` symbol.
    *   **Number of Videos:** Specify how many *new* videos (not previously processed) you want the application to find and process.
    *   **Start:** Click the "Start Scraping & Editing" button.

3.  **Monitor Progress:**
    *   The application will first use Selenium to browse TikTok, find video links, and then download them using `yt-dlp`.
    *   Downloaded videos are saved to the `videos/` directory.
    *   Each valid downloaded video will then be edited using FFmpeg (mirrored and cropped by default).
    *   Edited videos are saved to the `edited_videos/` directory.
    *   The log area in the GUI will display detailed messages about the process.
    *   The status bar will show the current high-level task.
    *   A progress bar will indicate the overall progress of downloading and editing the found videos.

4.  **Output:**
    *   Original downloaded videos: `videos/<video_id>.mp4`
    *   Edited videos: `edited_videos/<video_id>_edited_ffmpeg.mp4`
    *   Processed video IDs are logged in `data/processed_videos.txt` to avoid reprocessing.

## ⚙️ How It Works

1.  **GUI Interaction (`main.py`):**
    *   The user provides a hashtag and the number of new videos to fetch.
    *   The main application validates input and starts a background thread for processing.

2.  **Scraping (`scraper.py`):**
    *   **WebDriver Setup:** Initializes a Selenium Chrome WebDriver.
    *   **Navigate to Hashtag Page:** Opens the TikTok page for the given hashtag.
    *   **Scroll and Find Links:** Scrolls the page to load video elements and extracts direct video URLs. It checks against `data/processed_videos.txt` to only consider new videos.
    *   **Video Downloading (`yt-dlp`):** For each new video URL, `yt-dlp` is called as a subprocess to download the video into the `videos/` folder.
    *   **Download Verification (`ffprobe`):** After download, `ffprobe` (part of FFmpeg) is used to verify the integrity of the video file. Corrupted or empty files are typically discarded.

3.  **Editing (`editor.py`):**
    *   For each successfully downloaded and verified video:
        *   `ffprobe` is first used to get the video's dimensions for accurate cropping.
        *   `ffmpeg` is called as a subprocess to apply edits (default: horizontal flip and percentage-based crop).
        *   The edited video is saved in the `edited_videos/` folder.
    *   Upon successful editing, the video ID is added to `data/processed_videos.txt` by the main worker.

4.  **Logging and Status (`utils.py`, `main.py`):**
    *   Throughout the process, logs and status updates are sent from the worker thread to the GUI via a queue.
    *   `utils.py` contains helper functions for managing the processed videos list and timestamps.

## 📂 Project Structure

```
TTVideo/
├── data/                     # Stores persistent data
│   └── processed_videos.txt  # List of processed video IDs
├── edited_videos/            # Output directory for edited videos
├── TTVideo/                  # (Likely a leftover, consider removing or clarifying its purpose)
├── videos/                   # Output directory for original downloaded videos
├── .gitignore                # (Recommended) Specifies intentionally untracked files
├── check_path.py             # Utility to check Python's sys.path
├── editor.py                 # Handles video editing logic using FFmpeg
├── install.bat               # Batch script to install Python dependencies
├── main.py                   # Main application script with the GUI (CustomTkinter)
├── README.md                 # This file
├── requirements.txt          # Python package dependencies
├── scraper.py                # Handles TikTok scraping and video downloading
├── start.bat                 # Batch script to run the application
└── utils.py                  # Utility functions (e.g., timestamp, processed video tracking)
```

## 🔗 Dependencies

*   **Python Packages:** (defined in `requirements.txt`)
    *   `customtkinter`: For the graphical user interface.
    *   `selenium`: For browser automation to scrape TikTok.
    *   `webdriver-manager`: To manage the ChromeDriver for Selenium.
    *   `tiktok-scraper`: (Currently imported in `scraper.py` but primary scraping logic uses Selenium. Its direct use could be expanded or phased out).
    *   `yt-dlp`: While listed for pip install, it's primarily used as a command-line tool.

*   **External Tools:** (must be installed separately and added to system PATH)
    *   **Google Chrome:** Required by Selenium.
    *   **FFmpeg:** For video editing (`ffmpeg`) and verification (`ffprobe`).
    *   **yt-dlp:** For downloading videos.

## 🔧 Troubleshooting

*   **"FFmpeg not found" / "yt-dlp not found":**
    *   Ensure FFmpeg (which includes `ffmpeg.exe` and `ffprobe.exe`) and `yt-dlp.exe` are installed.
    *   **Crucially, verify that the directories containing these executables are added to your system's PATH environment variable.** You might need to restart your terminal or PC after updating PATH.
    *   You can check by opening a new command prompt and typing `ffmpeg -version` and `yt-dlp --version`.

*   **WebDriver Errors / Chrome Issues:**
    *   Make sure Google Chrome is installed and up-to-date.
    *   `webdriver-manager` should handle ChromeDriver, but if issues persist, ensure no antivirus or firewall is blocking its download or execution.
    *   "SessionNotCreatedException" or similar: Could be a mismatch between Chrome version and ChromeDriver version. `webdriver-manager` aims to prevent this. Try clearing webdriver-manager's cache (`~/.wdm` directory).

*   **TikTok Scraping Fails (No videos found, CAPTCHAs):**
    *   TikTok frequently updates its website structure, which can break the XPaths used for scraping. The XPaths in `scraper.py` might need updating.
    *   If CAPTCHAs appear, Selenium might get stuck. The current script waits for the page to load and may require manual CAPTCHA solving in the opened Chrome window.
    *   Consider running the browser in non-headless mode (default in `scraper.py`) to observe any issues.
    *   Using a VPN or proxy might sometimes be necessary if your IP is flagged.

*   **Videos Downloaded are Corrupt or Zero Size:**
    *   `yt-dlp` usually handles this well, and `ffprobe` verification aims to catch these.
    *   Network issues during download can cause this.
    *   If it happens consistently, check `yt-dlp` logs (though the app captures its stderr) or try downloading a problematic URL manually with `yt-dlp` in verbose mode.

*   **Python Dependencies Not Found:**
    *   Ensure you have activated your virtual environment (if using one) before running `pip install -r requirements.txt` or `python main.py`.

*   **Permission Errors:**
    *   Ensure the application has write permissions for the `videos/`, `edited_videos/`, and `data/` directories.

## 📜 Disclaimer

*   This tool is for educational and personal use only.
*   Downloading copyrighted material without permission may be illegal in your country. Please respect copyright laws and TikTok's Terms of Service.
*   The developers of this tool are not responsible for any misuse.
*   TikTok's website structure can change, potentially breaking the scraping functionality. Maintenance may be required.