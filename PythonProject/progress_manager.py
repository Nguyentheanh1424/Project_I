import json
import os
from tkinter import messagebox

class ProgressManager:
    def __init__(self):
        self.settings = {
            "zip_path": None,
            "mode": None,
            "number_workers": 0,
            "charset": None,
            "max_length": 0,
            "current_length": 1,
            "current_index": 0,
            "passwords_tried":0,
            "wordlist_path": None,
        }
        self.progress_file = "progress.json"

    def save_progress(self, current_index, passwords_tried):
        try:
            progress_data = {
                "zip_path": self.settings.get("zip_path"),
                "mode": self.settings.get("mode"),
                "number_workers": self.settings.get("number_workers"),
                "charset": self.settings.get("charset"),
                "max_length": self.settings.get("max_length"),
                "current_length": self.settings.get("current_length"),
                "current_index": current_index,
                "passwords_tried": passwords_tried,
                "wordlist_path": self.settings.get("wordlist_path")
            }

            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=4)

        except Exception as e:
            messagebox.showerror("Error", f"Error saving progress: {e}")

    def load_progress(self, mode, charset = None, max_length = 0, wordlist_path = None):
        try:
            if not os.path.exists(self.progress_file):
                return None
            with open(self.progress_file, "r") as file:
                saved_settings = json.load(file)
                print("Saved settings:", saved_settings)
                if saved_settings.get("mode") != mode:
                    return None
                if saved_settings.get("mode") == "Brute Force":
                    if saved_settings.get("charset") != charset:
                        return None
                    if saved_settings.get("max_length") != max_length:
                        return None
                if saved_settings.get("mode") == "Dictionary Attack":
                    if saved_settings.get("wordlist_path") != wordlist_path:
                        return None
                if messagebox.askyesno("Resume", "Do you want to resume the last saved progress?"):
                    return saved_settings
        except Exception as e:
            messagebox.showerror("Error", f"Error loading progress: {e}")
        return None

    def delete_progress(self):
        if os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi khi xóa tiến trình: {e}")