import json
import os
from tkinter import messagebox

class ProgressManager:
    def __init__(self):
        self.settings = {
            "mode": None,                   # Chế độ tấn công (Brute force hoặc Dictionary Attack)
            "zip_path": None,               # Đường dẫn file zip
            "charset": None,                # Bộ ký tự
            "number_workers": 0,            # Số tiến trình thực hiện
            "max_length": 0,                # Độ dài mật khẩu tối đa
            "current_length": 0,            # Độ dài mật khẩu hiện tại
            "current_index": 0,             # Chỉ số hiện tại
            "wordlist_path": None           # Đường dẫn danh sách mật khẩu
        }
        self.progress_file = "progress.json"  # Tên file lưu tiến trình

    def save_progress(self, index_min):
        try:
            self.settings["current_index"] = index_min
            with open(self.progress_file, "w") as file:
                json.dump(self.settings, file, indent=4)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lưu tiến trình: {e}")

    def load_progress(self, mode):
        if not os.path.exists(self.progress_file):
            return None

        try:
            with open(self.progress_file, "r") as file:
                saved_settings = json.load(file)

            if mode == "Brute Force":
                if (saved_settings["zip_path"] == self.settings["zip_path"] and
                        saved_settings["max_length"] == self.settings["max_length"] and
                        saved_settings["charset"] == self.settings["charset"]):
                    if messagebox.askyesno(
                            "Tìm thấy tiến trình đã lưu",
                            "Bạn có muốn tiếp tục từ lần dừng trước không?"):
                        return saved_settings

            elif mode == "Dictionary Attack":
                if (saved_settings["zip_path"] == self.settings["zip_path"] and
                        saved_settings["wordlist_path"] == self.settings["wordlist_path"]):
                    if messagebox.askyesno(
                            "Tìm thấy tiến trình đã lưu",
                            "Bạn có muốn tiếp tục từ lần dừng trước không?"):
                        return saved_settings

        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi tải tiến trình: {e}")
        return None

    def delete_progress(self):
        if os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi khi xóa tiến trình: {e}")