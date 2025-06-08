# This file will contain utility functions, e.g., for managing processed video IDs. 

import os
import datetime

PROCESSED_VIDEOS_FILE = os.path.join("data", "processed_videos.txt")

def get_timestamp():
    """Returns the current time as a formatted string."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_processed_videos(filepath=PROCESSED_VIDEOS_FILE):
    """
    Loads the set of processed video IDs from the specified file.
    Returns an empty set if the file doesn't exist.
    """
    if not os.path.exists(filepath):
        # Create the data directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        return set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        print(f"Error loading processed videos: {e}")
        return set()

def add_processed_video(video_id, filepath=PROCESSED_VIDEOS_FILE):
    """
    Adds a video ID to the processed videos file.
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"{video_id}\n")
        return True
    except Exception as e:
        print(f"Error adding processed video: {e}")
        return False

def is_video_processed(video_id, filepath=PROCESSED_VIDEOS_FILE):
    """
    Checks if a video ID has already been processed.
    """
    processed_videos = get_processed_videos(filepath)
    return video_id in processed_videos

if __name__ == '__main__':
    # Test functions
    test_file = os.path.join("data", "test_processed.txt")
    if os.path.exists(test_file):
        os.remove(test_file)

    print(f"Initial processed videos: {get_processed_videos(test_file)}")
    print(f"Is 'video1' processed? {is_video_processed('video1', test_file)}")

    add_processed_video('video1', test_file)
    print(f"After adding 'video1': {get_processed_videos(test_file)}")
    print(f"Is 'video1' processed? {is_video_processed('video1', test_file)}")

    add_processed_video('video2', test_file)
    add_processed_video('video1', test_file) # Adding duplicate
    print(f"After adding 'video2' and duplicate 'video1': {get_processed_videos(test_file)}")
    print(f"Is 'video2' processed? {is_video_processed('video2', test_file)}")
    print(f"Is 'video3' processed? {is_video_processed('video3', test_file)}")

    # Clean up test file
    if os.path.exists(test_file):
        os.remove(test_file)
    print("Test complete.") 