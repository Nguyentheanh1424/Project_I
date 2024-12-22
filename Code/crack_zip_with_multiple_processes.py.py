import json
import logging
import multiprocessing
import os
import sys
import threading
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, IntVar, ttk, messagebox

import pyzipper

# Đặt mã hóa UTF-8 để hỗ trợ tiếng Việt
sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(processName)s] %(levelname)s: %(message)s',
    handlers=[logging.FileHandler('zip_crack.log', encoding='utf-8')]
)

PROGRESS_FILE = "progress.json"

# Kiểm tra file ZIP
def _validate_zip_file(zip_file: str) -> bool:
    """Kiểm tra nếu tệp ZIP tồn tại và hợp lệ."""
    if not os.path.isfile(zip_file):
        logging.error(f"Tệp ZIP không tồn tại: {zip_file}")
        return False
    try:
        with pyzipper.AESZipFile(zip_file, 'r') as zf:
            zf.testzip()  # Kiểm tra file
    except pyzipper.BadZipFile:
        logging.error("Tệp ZIP không hợp lệ.")
        return False
    return True


# Lưu tiến trình
def _save_progress(progress, settings):
    """Lưu tiến độ hiện tại và thông tin cấu hình."""
    progress.update({
        "zip_file": settings["zip_file"],
        "max_password_length": settings["max_password_length"],
        "character_set": settings["character_set"]
    })
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=4)
        logging.info(f"Tiến độ đã được lưu: {progress}")
    except Exception as e:
        logging.error(f"Lỗi khi lưu tiến độ: {e}")


# Tải tiến trình đã lưu
def _load_progress():
    """Tải tiến độ đã lưu."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Lỗi khi tải tiến độ: {e}")
    return None


# Xóa tiến trình
def _delete_progress():
    """Xóa file tiến độ."""
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        logging.info("File tiến độ đã được xóa.")


# Tạo chunk mật khẩu
def _generate_password_chunk(chars, length, start, chunk_size):
    """Tạo một phần mật khẩu."""
    base = len(chars)
    chunk = []
    for i in range(start, start + chunk_size):
        if i >= base ** length:
            break
        password = ""
        idx = i
        for _ in range(length):
            password = chars[idx % base] + password
            idx //= base
        chunk.append(password)
    return chunk


# Worker giải mã mật khẩu
def _crack_worker(zip_file, password, stop_flag):
    """Tiến trình làm việc để thử mật khẩu ZIP."""
    if stop_flag.is_set():
        return None
    try:
        with pyzipper.AESZipFile(zip_file, 'r') as zf:
            zf.extractall(pwd=password.encode('utf-8'))  # Giải mã bằng mật khẩu
        return password  # Mật khẩu thành công
    except (RuntimeError, pyzipper.BadZipFile):
        return None  # Mật khẩu không chính xác
    except Exception as e:
        logging.error(f"Lỗi không mong muốn: {e}")
        return None


# Hàm xử lý chính GUI
def start_cracking_gui(settings, progress_var, status_label):
    zip_file = settings["zip_file"]
    char_set = settings["character_set"]
    max_length = settings["max_password_length"]
    chunk_size = 1000
    stop_flag = multiprocessing.Manager().Event()

    # Khởi tạo trạng thái từ tiến trình đã lưu
    progress = _load_progress() or {"current_length": 1, "current_index": 0}

    for length in range(progress["current_length"], max_length + 1):
        total_combinations = len(char_set) ** length
        status_label.config(text=f"Đang thử mật khẩu độ dài {length}...")

        for start in range(progress["current_index"], total_combinations, chunk_size):
            passwords = _generate_password_chunk(char_set, length, start, chunk_size)
            for password in passwords:
                if stop_flag.is_set():
                    _save_progress({"current_length": length, "current_index": start}, settings)
                    return
                result = _crack_worker(zip_file, password, stop_flag)
                if result:
                    messagebox.showinfo("Thành công", f"Mật khẩu đã giải mã thành công: {result}")
                    _delete_progress()
                    return

            progress_var.set((start + chunk_size) / total_combinations * 100)

        progress["current_index"] = 0
        progress["current_length"] += 1

    messagebox.showinfo("Kết quả", "Không tìm thấy mật khẩu.")


# GUI chính
def main_gui():
    root = Tk()
    root.title("Giải Mã ZIP")
    root.geometry("500x300")

    # Các biến
    zip_file_var = StringVar()
    max_length_var = IntVar(value=1)
    char_set_var = StringVar(value="lowercase+digits")
    process_var = IntVar(value=multiprocessing.cpu_count())
    progress_var = IntVar(value=0)

    # Label và Entry
    Label(root, text="Tệp ZIP:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=zip_file_var, width=50).pack(anchor="w", padx=10)

    Button(root, text="Chọn tệp ZIP", command=lambda: zip_file_var.set(filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")]))).pack(anchor="w", padx=10)

    Label(root, text="Độ dài mật khẩu tối đa:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=max_length_var).pack(anchor="w", padx=10)

    Label(root, text="Bộ ký tự:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=char_set_var).pack(anchor="w", padx=10)

    Label(root, text="Số tiến trình:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=process_var).pack(anchor="w", padx=10)

    # Nút bắt đầu
    status_label = Label(root, text="Chưa bắt đầu.")
    status_label.pack(pady=10)

    Button(
        root,
        text="Bắt đầu giải mã",
        command=lambda: threading.Thread(target=start_cracking_gui, args=({
            "zip_file": zip_file_var.get(),
            "max_password_length": max_length_var.get(),
            "character_set": char_set_var.get(),
            "max_processes": process_var.get()
        }, progress_var, status_label)).start()
    ).pack(pady=10)

    # Thanh tiến trình
    ttk.Progressbar(root, variable=progress_var, maximum=100).pack(fill="x", padx=10, pady=10)

    # Chạy GUI
    root.mainloop()


if __name__ == "__main__":
    main_gui()
