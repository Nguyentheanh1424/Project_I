import json
import os
from tkinter import messagebox

class ProgressManager:
    def __init__(self, progress_file):
        self.progress_file = progress_file

    def save_progress(self, progress, settings, current_length, current_index):
        progress.update({
            "zip_file": settings["zip_file"],
            "max_password_length": settings["max_password_length"],
            "character_set": settings["character_set"],
            "current_length": current_length,
            "current_index": current_index
        })
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(progress, f, indent=4)
        except Exception as e:
            print(f"Error occurred: {e}")

    def load_progress(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                self.delete_progress()
        return None

    def delete_progress(self):
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)

    def validate_progress(self, settings):
        progress = self.load_progress()
        if not progress:
            return False

        required_keys = ["zip_file", "max_password_length", "character_set",
                        "current_length", "current_index"]
        if not all(key in progress for key in required_keys):
            return False

        if (progress["zip_file"] == settings["zip_file"] and
                progress["max_password_length"] == settings["max_password_length"] and
                progress["character_set"] == settings["character_set"] and
                progress["current_length"] != 0 and
                progress["current_index"] != 0):
            response = messagebox.askquestion(
                "Tìm thấy tiến trình cũ",
                "Bạn có muốn tiếp tục thực hiện từ lần dừng trước không?."
            )
            return response == "yes"
        return False