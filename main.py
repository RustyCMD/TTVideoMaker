import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import queue
import time # For demo purposes or small delays
import traceback # <--- Added this import
import os # For checking paths

# Local imports
import scraper
import editor
import utils

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TikTok Video Scraper & Editor")
        self.geometry("900x750") # Slightly taller for new field

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Log area will expand (changed from 2 to 1 for direct content)

        # --- Top Frame for Controls ---
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.controls_frame, text="TikTok Video Scraper & Editor", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(0,10))

        # --- Hashtag Input ---
        self.hashtag_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.hashtag_frame.pack(pady=5, fill="x", padx=20)
        
        self.hashtag_label = ctk.CTkLabel(self.hashtag_frame, text="Hashtag (e.g., funnycats):")
        self.hashtag_label.pack(side="left", padx=(0,10))
        
        self.hashtag_entry = ctk.CTkEntry(self.hashtag_frame, placeholder_text="Enter hashtag without #")
        self.hashtag_entry.pack(side="left", fill="x", expand=True)
        # --- End Hashtag Input ---

        # Number of videos to scrape
        self.num_videos_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.num_videos_frame.pack(pady=5, fill="x", padx=20)
        
        self.num_videos_label = ctk.CTkLabel(self.num_videos_frame, text="Number of NEW videos to process:")
        self.num_videos_label.pack(side="left", padx=(0,10))
        
        self.num_videos_entry = ctk.CTkEntry(self.num_videos_frame, placeholder_text="e.g., 5", width=100)
        self.num_videos_entry.pack(side="left")
        self.num_videos_entry.insert(0, "3")

        # Start Button
        self.start_button = ctk.CTkButton(self.controls_frame, text="Start Scraping & Editing", command=self.start_scraping_thread)
        self.start_button.pack(pady=10, padx=20, fill="x")
        
        self.progress_bar = ctk.CTkProgressBar(self.controls_frame, mode='determinate')
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(5,10), padx=20, fill="x")

        # --- Log Area ---
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", wrap="word", height=300)
        self.log_textbox.grid(row=1, column=0, padx=20, pady=(0,10), sticky="nsew")

        # --- Status Label (Bottom) ---
        self.status_bar_frame = ctk.CTkFrame(self, height=30)
        self.status_bar_frame.grid(row=2, column=0, padx=20, pady=(5,10), sticky="ew")
        self.status_label = ctk.CTkLabel(self.status_bar_frame, text="Status: Idle")
        self.status_label.pack(side="left", padx=10)

        # Queue for thread communication
        self.log_queue = queue.Queue()
        self.after(100, self.process_log_queue) # Periodically check the queue

        self.is_scraping = False
        self.stop_event = threading.Event()

    def log_message(self, message, level="INFO"):
        """Adds a message to the log textbox."""
        timestamp = utils.get_timestamp()
        formatted_message = f"[{timestamp} - {level}] {message}\n"
        
        self.log_textbox.configure(state="normal")
        if level == "ERROR" or level == "CRITICAL":
            self.log_textbox.insert("end", formatted_message, f"log_{level.lower()}")
            self.log_textbox.tag_config(f"log_{level.lower()}", foreground="red")
        elif level == "WARNING":
            self.log_textbox.insert("end", formatted_message, f"log_{level.lower()}")
            self.log_textbox.tag_config(f"log_{level.lower()}", foreground="orange")
        elif level == "SUCCESS":
            self.log_textbox.insert("end", formatted_message, f"log_{level.lower()}")
            self.log_textbox.tag_config(f"log_{level.lower()}", foreground="green")
        else:
            self.log_textbox.insert("end", formatted_message)
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end") # Scroll to the end
        self.update_idletasks() # Ensure UI updates

    def process_log_queue(self):
        """Processes messages from the log queue and updates the GUI."""
        try:
            while True: # Process all messages currently in the queue
                item = self.log_queue.get_nowait()
                if item[0] == "LOG":
                    _, msg, level = item
                    self.log_message(msg, level)
                elif item[0] == "STATUS_UPDATE":
                    _, msg = item
                    self.status_label.configure(text=f"Status: {msg}")
                elif item[0] == "PROGRESS_UPDATE":
                    _, value = item # value between 0 and 1
                    self.progress_bar.set(value)
                elif item[0] == "TASK_COMPLETE":
                    _, msg = item
                    self.log_message(msg, "INFO")
                    self.status_label.configure(text=f"Status: {msg}")
                    self.start_button.configure(state="normal", text="Start Scraping & Editing")
                    self.is_scraping = False
                    self.progress_bar.set(1) # Ensure progress bar is full on completion
                    messagebox.showinfo("Process Complete", msg)
                    break # Exit loop for this specific TASK_COMPLETE handling to avoid blocking
                elif item[0] == "TASK_FAILED":
                    _, msg = item
                    self.log_message(msg, "ERROR")
                    self.status_label.configure(text=f"Status: Failed - {msg}")
                    self.start_button.configure(state="normal", text="Start Scraping & Editing")
                    self.is_scraping = False
                    messagebox.showerror("Process Failed", msg)
                    break # Exit loop for this specific TASK_FAILED handling
        except queue.Empty:
            pass # No more messages
        except Exception as e:
            # Log unexpected errors in queue processing to the textbox itself if possible
            self.log_message(f"Error processing log queue: {e}", "CRITICAL")
            traceback_str = traceback.format_exc()
            self.log_message(traceback_str, "DEBUG")
        finally:
            self.after(100, self.process_log_queue) # Reschedule

    def start_scraping_thread(self):
        """Starts the scraping and editing process in a new thread."""
        if self.is_scraping:
            self.log_message("Process already running.", "WARNING")
            messagebox.showwarning("Busy", "A scraping and editing process is already running.")
            return

        hashtag = self.hashtag_entry.get().strip()
        if not hashtag:
            self.log_message("Hashtag cannot be empty.", "ERROR")
            messagebox.showerror("Invalid Input", "Please enter a hashtag.")
            return
        if "#" in hashtag:
            self.log_message("Please enter the hashtag without the '#' symbol.", "ERROR")
            messagebox.showerror("Invalid Input", "Please enter the hashtag without the '#' symbol.")
            return

        try:
            num_videos = int(self.num_videos_entry.get())
            if num_videos <= 0:
                self.log_message("Number of videos must be a positive integer.", "ERROR")
                messagebox.showerror("Invalid Input", "Please enter a positive number of videos.")
                return
        except ValueError:
            self.log_message("Invalid input for number of videos. Please enter an integer.", "ERROR")
            messagebox.showerror("Invalid Input", "Number of videos must be an integer.")
            return

        self.is_scraping = True
        self.stop_event.clear()
        self.start_button.configure(state="disabled", text="Processing...")
        self.progress_bar.set(0)
        self.status_label.configure(text=f"Starting process for hashtag: {hashtag}...")
        self.log_message(f"Starting process for hashtag '{hashtag}' to find {num_videos} new videos...")

        thread = threading.Thread(target=self.scraping_worker, args=(hashtag, num_videos,), daemon=True)
        thread.start()

    def scraping_worker(self, hashtag, num_videos_to_find):
        """The actual work of scraping, downloading, and editing. Now uses tiktok-scraper."""
        try:
            self.log_queue.put(("LOG", "Initializing TikTok scraping process...", "INFO"))
            self.log_queue.put(("STATUS_UPDATE", f"Starting to scrape #{hashtag}..."))
            
            # Call the new scraper function
            # This function is expected to handle downloads and return a list of dicts:
            # [{'id': 'video_id1', 'filepath': 'path/to/video1.mp4'}, ...]
            downloaded_video_infos = scraper.scrape_and_download_videos_by_hashtag(
                hashtag=hashtag, 
                num_videos_to_find=num_videos_to_find, 
                log_queue=self.log_queue
            )

            if not downloaded_video_infos:
                self.log_queue.put(("LOG", f"No new, valid videos found or downloaded for hashtag '{hashtag}'.", "WARNING"))
                self.log_queue.put(("TASK_COMPLETE", f"No new videos processed for #{hashtag}."))
                return

            self.log_queue.put(("LOG", f"Found {len(downloaded_video_infos)} new, valid video(s) to process.", "INFO"))
            self.log_queue.put(("STATUS_UPDATE", "Starting video editing process..."))
            
            total_videos_to_process = len(downloaded_video_infos)
            edited_count = 0
            failed_edits = 0

            for i, video_info in enumerate(downloaded_video_infos):
                # Add this check to allow for a graceful stop
                if self.stop_event.is_set():
                    self.log_queue.put(("LOG", "Stop requested by user. Halting process.", "WARNING"))
                    break

                video_id = video_info.get('id')
                original_filepath = video_info.get('filepath')

                if not video_id or not original_filepath:
                    self.log_queue.put(("LOG", f"Skipping an item due to missing ID or filepath: {video_info}", "WARNING"))
                    failed_edits += 1
                    continue

                self.log_queue.put(("LOG", f"--- Processing video {video_id} ({i+1}/{total_videos_to_process}) ---", "INFO"))
                self.log_queue.put(("STATUS_UPDATE", f"Editing video {video_id} ({i+1}/{total_videos_to_process})..."))
                
                edited_video_path = editor.edit_video(original_filepath, video_id, log_queue=self.log_queue)
                
                if edited_video_path:
                    self.log_queue.put(("LOG", f"Video {video_id} edited successfully: {edited_video_path}", "SUCCESS"))
                    utils.add_processed_video(video_id) # Add to processed list *after* successful edit
                    edited_count += 1
                else:
                    self.log_queue.put(("LOG", f"Failed to edit video {video_id}. It might have been skipped or an error occurred.", "ERROR"))
                    # We don't add to processed_videos.txt if editing failed, so it might be retried later.
                    # The original downloaded file might still exist unless editor.py or scraper.py deleted it due to corruption.
                    failed_edits +=1
                
                current_progress = (i + 1) / total_videos_to_process
                self.log_queue.put(("PROGRESS_UPDATE", current_progress))

            final_message = f"Process finished for hashtag '{hashtag}'. Successfully edited: {edited_count}/{total_videos_to_process}. Failed/Skipped: {failed_edits}."
            if failed_edits > 0:
                final_message += " Check logs for details on failures."
            self.log_queue.put(("TASK_COMPLETE", final_message))

        except Exception as e:
            self.log_queue.put(("LOG", f"Scraping worker encountered an unhandled error: {e}", "CRITICAL"))
            import traceback
            self.log_queue.put(("LOG", traceback.format_exc(), "DEBUG"))
            self.log_queue.put(("TASK_FAILED", "Critical error in backend process. Check logs."))
        finally:
            # Removed WebDriver cleanup as it's no longer used here
            self.log_queue.put(("LOG", "Scraping and editing worker thread finished.", "DEBUG"))

    def on_closing(self):
        """Handle window closing event."""
        if self.is_scraping:
            if messagebox.askyesno("Confirm Exit", "A process is running. Are you sure you want to exit? The current step will finish, then the app will close."):
                self.log_message("Exit requested. The process will stop after the current task.", "INFO")
                self.stop_event.set() # Signal the worker thread to stop
                self.destroy() # Close the window
            else:
                return # Do not close
        else:
            self.destroy()


if __name__ == "__main__":
    # Ensure necessary directories exist before app starts
    os.makedirs("videos", exist_ok=True)
    os.makedirs("edited_videos", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Optional: Set the appearance mode and default color theme
    ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"
    
    if not editor.check_ffmpeg():
        # Log to console as GUI might not be up yet for queue
        print("[CRITICAL] FFmpeg not found in PATH. Please install FFmpeg and add its bin directory to your system PATH.")
        print("[CRITICAL] Download FFmpeg from https://ffmpeg.org/download.html")
        # Allow app to start, but editing will fail. check_ffmpeg in editor.py will log to GUI too.
    
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing) # Handle window close button
    app.mainloop() 