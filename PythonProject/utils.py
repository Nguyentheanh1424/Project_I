import json
import logging
import os

PROGRESS_FILE = "progress.json"

def save_progress(progress, settings):
    """Lưu tiến trình vào file."""
    progress.update(settings)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=4)
    logging.info(f"Đã lưu tiến trình: {progress}")

def load_progress():
    """Tải tiến trình đã lưu."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logging.error("Tệp tiến độ bị lỗi.")
    return None

def delete_progress():
    """Xóa tệp tiến độ."""
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        logging.info("Đã xóa tệp tiến độ.")
