# This file will contain video editing functions. 

import os
import subprocess
import shutil # To check for ffmpeg

EDITED_VIDEOS_DIR = "edited_videos"

# Ensure output directory exists
os.makedirs(EDITED_VIDEOS_DIR, exist_ok=True)

def _log(message, level="INFO", log_queue=None):
    """Helper function to log to queue or print."""
    if log_queue:
        log_queue.put(("LOG", message, level)) # Ensure this format for GUI
    else:
        print(f"[{level}] {message}")

def check_ffmpeg():
    """Checks if ffmpeg is accessible in the system PATH."""
    return shutil.which("ffmpeg") is not None

def edit_video(input_video_path, video_id, edits=None, log_queue=None):
    """
    Applies specified edits to the input video using FFmpeg and saves it.
    Args:
        input_video_path (str): Path to the original video file.
        video_id (str): The ID of the video, used for naming the output file.
        edits (dict, optional): Dict specifying edits. e.g., {"mirror": True, "crop_percent": 5}
        log_queue (queue.Queue, optional): Queue for sending log messages to GUI.
    Returns:
        str: Path to the edited video, or None if an error occurred.
    """
    if not check_ffmpeg():
        _log("FFmpeg not found in PATH. Please install FFmpeg and add it to your system PATH.", "CRITICAL", log_queue)
        _log("Download FFmpeg from https://ffmpeg.org/download.html", "CRITICAL", log_queue)
        return None

    if not os.path.exists(input_video_path):
        _log(f"Input video not found at {input_video_path}", "ERROR", log_queue)
        return None

    output_filename = f"{video_id}_edited_ffmpeg.mp4"
    output_video_path = os.path.join(EDITED_VIDEOS_DIR, output_filename)

    if edits is None:
        edits = {
            "mirror": True,
            "crop_percent": 2, # Crop 2% from each side
        }

    try:
        _log(f"Starting FFmpeg editing for: {input_video_path}", "INFO", log_queue)
        if log_queue: log_queue.put(("STATUS_UPDATE", f"Editing video {video_id} with FFmpeg..."))

        # Get video dimensions for cropping calculation
        ffprobe_cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0",
            input_video_path
        ]
        
        process_probe = subprocess.Popen(ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout_probe, stderr_probe = process_probe.communicate(timeout=10)

        if process_probe.returncode != 0:
            _log(f"ffprobe failed to get video dimensions for {video_id}. Error: {stderr_probe}", "ERROR", log_queue)
            return None
        
        try:
            original_width, original_height = map(int, stdout_probe.strip().split('x'))
            _log(f"Original dimensions for {video_id}: {original_width}x{original_height}", "DEBUG", log_queue)
        except ValueError as e:
            _log(f"Could not parse dimensions from ffprobe output '{stdout_probe.strip()}': {e}", "ERROR", log_queue)
            return None

        video_filters = []

        # 1. Mirroring (Horizontal Flip)
        if edits.get("mirror"):
            _log("Applying horizontal flip (mirroring) with FFmpeg...", "DEBUG", log_queue)
            video_filters.append("hflip")

        # 2. Cropping (as a percentage from borders)
        crop_percent = edits.get("crop_percent", 0)
        if crop_percent > 0 and crop_percent < 50:
            # Calculate crop dimensions
            crop_w_each_side = int(original_width * (crop_percent / 100.0))
            crop_h_each_side = int(original_height * (crop_percent / 100.0))
            
            out_w = original_width - (2 * crop_w_each_side)
            out_h = original_height - (2 * crop_h_each_side)
            offset_x = crop_w_each_side
            offset_y = crop_h_each_side
            
            # Ensure dimensions are even, as some codecs prefer it
            out_w = out_w if out_w % 2 == 0 else out_w -1
            out_h = out_h if out_h % 2 == 0 else out_h -1
            if out_w <=0 or out_h <=0:
                _log(f"Crop dimensions result in invalid output size for {video_id}. Skipping crop.", "WARNING", log_queue)
            else:
                crop_filter = f"crop={out_w}:{out_h}:{offset_x}:{offset_y}"
                _log(f"Applying crop with FFmpeg: {crop_filter}", "DEBUG", log_queue)
                video_filters.append(crop_filter)

        ffmpeg_cmd = ["ffmpeg", "-y", "-i", input_video_path]
        if video_filters:
            ffmpeg_cmd.extend(["-vf", ",".join(video_filters)])
        
        # Add common output options for reasonable quality and compatibility
        ffmpeg_cmd.extend([
            "-c:v", "libx264",         # Video codec
            "-preset", "medium",        # Encoding speed/quality trade-off
            "-crf", "23",               # Constant Rate Factor (quality, lower is better, 18-28 is typical)
            "-c:a", "aac",             # Audio codec
            "-b:a", "128k",            # Audio bitrate
            output_video_path
        ])

        _log(f"Executing FFmpeg command: {' '.join(ffmpeg_cmd)}", "DEBUG", log_queue)
        if log_queue: log_queue.put(("STATUS_UPDATE", f"Applying FFmpeg edits for {video_id}..."))

        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(timeout=120) # 2-minute timeout for encoding

        if process.returncode == 0 and os.path.exists(output_video_path) and os.path.getsize(output_video_path) > 0:
            _log(f"FFmpeg edited video saved successfully: {output_video_path}", "SUCCESS", log_queue)
            return output_video_path
        else:
            _log(f"FFmpeg editing failed for {video_id}. Return code: {process.returncode}", "ERROR", log_queue)
            _log(f"FFmpeg stdout: {stdout}", "DEBUG", log_queue)
            _log(f"FFmpeg stderr: {stderr}", "ERROR", log_queue)
            if os.path.exists(output_video_path): # Clean up failed output
                try: os.remove(output_video_path)
                except OSError as e_rem: _log(f"Error removing failed FFmpeg output {output_video_path}: {e_rem}","WARNING", log_queue)
            return None

    except subprocess.TimeoutExpired:
        _log(f"FFmpeg command timed out for video {video_id}.", "ERROR", log_queue)
        if process: process.kill()
        stdout, stderr = process.communicate()
        _log(f"FFmpeg stdout (timeout): {stdout}", "DEBUG", log_queue)
        _log(f"FFmpeg stderr (timeout): {stderr}", "ERROR", log_queue)
        if os.path.exists(output_video_path): os.remove(output_video_path)
        return None
    except Exception as e:
        _log(f"Unexpected error during FFmpeg video editing for {input_video_path}: {e}", "ERROR", log_queue)
        if 'process' in locals() and process and process.poll() is None: process.kill() # Ensure process is killed if running
        if os.path.exists(output_video_path): 
            try: os.remove(output_video_path)
            except OSError as e_rem_ex: _log(f"Error removing file {output_video_path} on exception: {e_rem_ex}","WARNING", log_queue)
        return None

if __name__ == '__main__':
    # This test block will now rely on FFmpeg being in the PATH.
    _log("Video Editor Test Script (using FFmpeg directly)", "INFO")
    _log("--------------------------------------------------", "INFO")

    if not check_ffmpeg():
        _log("FFmpeg not found. Cannot run editor tests.", "CRITICAL")
        exit()
    else:
        _log("FFmpeg found in PATH.", "INFO")

    # For testing, we need a sample video. 
    # The previous dummy video creation used moviepy. We'll skip that for now.
    # Please manually place a video named "test_dummy_editor_video.mp4" in the "videos" directory for this test.
    
    dummy_video_dir = "videos"
    os.makedirs(dummy_video_dir, exist_ok=True)
    test_video_id = "test_dummy_ffmpeg_video"
    test_input_path = os.path.join(dummy_video_dir, "test_dummy_editor_video.mp4") # Re-use name for manual placement

    if os.path.exists(test_input_path):
        _log(f"\nTesting FFmpeg video editing with: {test_input_path}", "INFO")
        edited_path_default = edit_video(test_input_path, test_video_id) 
        if edited_path_default:
            _log(f"Default FFmpeg edit successful: {edited_path_default}", "SUCCESS")
        else:
            _log("Default FFmpeg edit failed.", "ERROR")

        _log("\nTesting with custom FFmpeg edits (no mirror, 10% crop)...", "INFO")
        custom_edits = {"mirror": False, "crop_percent": 10}
        edited_path_custom = edit_video(test_input_path, f"{test_video_id}_custom", edits=custom_edits)
        if edited_path_custom:
            _log(f"Custom FFmpeg edit successful: {edited_path_custom}", "SUCCESS")
        else:
            _log("Custom FFmpeg edit failed.", "ERROR")
        
        _log("\nTesting with non-existent input video...", "INFO")
        edit_video("non_existent_video.mp4", "non_existent_id")
        
        _log("\nCleaning up test files (if any created)...", "INFO")
        files_to_remove = [
            os.path.join(EDITED_VIDEOS_DIR, f"{test_video_id}_edited_ffmpeg.mp4"),
            os.path.join(EDITED_VIDEOS_DIR, f"{test_video_id}_custom_edited_ffmpeg.mp4")
        ]
        for f_path in files_to_remove:
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                    _log(f"Removed: {f_path}", "DEBUG")
                except OSError as e_rem_test:
                    _log(f"Error removing test file {f_path}: {e_rem_test}", "WARNING")
    else:
        _log(f"Test video {test_input_path} not found. Please place a video there to run editor tests.", "WARNING")

    _log("\nVideo Editor Test (FFmpeg) Finished.", "INFO") 