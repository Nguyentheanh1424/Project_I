import json
import os
from tkinter import messagebox


class ProgressManager:
    def __init__(self, progress_file):
        self.progress_file = progress_file

    def save_progress(self, mode, settings, **kwargs):
        """
        Lưu tiến trình hiện tại cho một chế độ tấn công cụ thể.

        Args:
            mode (str): Tên chế độ (ví dụ: "Brute Force", "Dictionary Attack").
            settings (dict): Cấu hình hiện tại.
            kwargs: Các thông tin bổ sung, ví dụ:
                - `current_length` (int): Độ dài mật khẩu (Brute Force).
                - `current_index` (int): Chỉ số hiện tại (Dictionary Attack).
                - `wordlist_path` (str): Đường dẫn tệp wordlist.
        """
        progress = {
            "mode": mode,
            "zip_file": settings.get("zip_file"),
            "max_password_length": settings.get("max_password_length"),
            "character_set": settings.get("character_set"),
        }
        progress.update(kwargs)
        try:
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(progress, f, indent=4)
        except Exception as e:
            print(f"Error occurred: {e}")

    def load_progress(self):
        """
        Tải trạng thái tiến trình đã lưu.

        Returns:
            dict | None: Trạng thái tiến trình hoặc `None` nếu không tồn tại.
        """
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Lỗi khi tải tiến trình: {e}")
                self.delete_progress()
        return None

    def delete_progress(self):
        """Xóa tệp tiến trình đã lưu."""
        if os.path.exists(self.progress_file):
            os.remove(self.progress_file)

    def validate_progress(self, mode, settings, **kwargs):
        """
        Kiểm tra tiến trình đã lưu có hợp lệ với chế độ hiện tại không.

        Args:
            mode (str): Tên chế độ (ví dụ: "Brute Force", "Dictionary Attack").
            settings (dict): Cấu hình hiện tại.
            kwargs: Các thông tin bổ sung cần kiểm tra.

        Returns:
            dict | None: Trạng thái tiến trình hợp lệ hoặc `None` nếu không hợp lệ.
        """
        progress = self.load_progress()
        if not progress:
            return None

        # Kiểm tra chế độ và các khóa cơ bản
        if progress.get("mode") != mode or progress.get("zip_file") != settings.get("zip_file"):
            return None

        # Kiểm tra các thông tin bổ sung tùy theo chế độ
        if mode == "Brute Force":
            if (progress.get("max_password_length") == settings.get("max_password_length") and
                    progress.get("character_set") == settings.get("character_set") and
                    progress.get("current_length", 0) > 0 and
                    progress.get("current_index", 0) > 0):
                return progress

        if mode == "Dictionary Attack":
            if (progress.get("wordlist_path") == kwargs.get("wordlist_path") and
                    progress.get("current_index", 0) > 0):
                return progress

        return None
