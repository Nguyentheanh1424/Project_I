import json
import logging
import multiprocessing
import os
import sys
import threading
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, IntVar, ttk, messagebox, BooleanVar, Checkbutton

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
    if not os.path.isfile(zip_file):
        logging.error(f"Tệp ZIP không tồn tại: {zip_file}")
        return False
    try:
        with pyzipper.AESZipFile(zip_file, 'r') as zf:
            zf.testzip()
    except pyzipper.BadZipFile:
        logging.error("Tệp ZIP không hợp lệ.")
        return False
    return True


# Lưu tiến trình
def _save_progress(progress, settings):
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
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logging.error("Tệp tiến độ bị hỏng. Sẽ bắt đầu từ đầu.")
            _delete_progress()
    return None  # Không có tiến trình hoặc tiến trình bị lỗi


# Xóa tiến trình
def _delete_progress():
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        logging.info("File tiến độ đã được xóa.")


# Kiểm tra tính hợp lệ của tiến trình đã lưu
def _validate_progress(settings):
    """Kiểm tra nếu tiến trình đã lưu phù hợp với cài đặt hiện tại."""
    progress = _load_progress()
    if not progress:
        return True  # Không có tiến trình, cho phép chạy từ đầu

    # Kiểm tra tính hợp lệ
    if (progress["zip_file"] != settings["zip_file"] or
            progress["max_password_length"] != settings["max_password_length"] or
            progress["character_set"] != settings["character_set"]):
        messagebox.showwarning(
            "Cảnh báo",
            "Thông tin tiến trình không phù hợp. Tiến trình cũ sẽ bị xóa và bắt đầu lại từ đầu."
        )
        _delete_progress()
        return False

    # Kiểm tra nếu index vượt quá số tổ hợp
    max_combinations = sum(len(settings["character_set"]) ** i for i in range(1, settings["max_password_length"] + 1))
    if progress.get("current_index", 0) >= max_combinations:
        messagebox.showwarning(
            "Cảnh báo",
            "Tiến trình đã lưu vượt quá số tổ hợp cho phép. Tiến trình sẽ bị xóa và bắt đầu lại từ đầu."
        )
        _delete_progress()
        return False

    return True


# Tạo chunk mật khẩu
def _generate_password_chunk(chars, length, start, chunk_size):
    base = len(chars)
    chunk = []
    total_combinations = base ** length
    for i in range(start, min(start + chunk_size, total_combinations)):  # Giới hạn chunk
        password = ""
        idx = i
        for _ in range(length):
            password = chars[idx % base] + password
            idx //= base
        chunk.append(password)
    return chunk


# Worker giải mã mật khẩu
def _crack_worker(zip_file, password, stop_flag):
    if stop_flag.is_set():
        return None
    try:
        with pyzipper.AESZipFile(zip_file, 'r') as zf:
            zf.extractall(pwd=password.encode('utf-8'))
        return password
    except (RuntimeError, pyzipper.BadZipFile):
        return None
    except Exception as e:
        logging.error(f"Lỗi không mong muốn: {e}")
        return None


# Chạy tiến trình giải mã
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
                    _delete_progress()  # Xóa tiến trình khi hoàn thành
                    return

            # Cập nhật tiến trình
            progress_var.set((start + chunk_size) / total_combinations * 100)

        progress["current_index"] = 0
        progress["current_length"] += 1

    messagebox.showinfo("Kết quả", "Không tìm thấy mật khẩu.")
    _delete_progress()  # Xóa tiến trình khi hoàn thành toàn bộ


# GUI chính
def main_gui():
    root = Tk()
    root.title("Giải Mã ZIP")
    root.geometry("300x450")

    # Các biến
    zip_file_var = StringVar()
    max_length_var = IntVar(value=1)
    process_var = IntVar(value=multiprocessing.cpu_count())
    progress_var = IntVar(value=0)

    # Bộ ký tự với Checkbox
    char_set_options = {
        "Lowercase": ("abcdefghijklmnopqrstuvwxyz", BooleanVar(value=True)),
        "Uppercase": ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", BooleanVar(value=False)),
        "Digits": ("0123456789", BooleanVar(value=True)),
        "Special": ("!@#$%^&*()-_=+[]{}|;:',.<>?/`~", BooleanVar(value=False)),
    }

    # Label và Entry
    Label(root, text="Tệp ZIP:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=zip_file_var, width=50).pack(anchor="w", padx=10)

    Button(root, text="Chọn tệp ZIP", command=lambda: zip_file_var.set(filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")]))).pack(anchor="w", padx=10)

    Label(root, text="Độ dài mật khẩu tối đa:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=max_length_var).pack(anchor="w", padx=10)

    Label(root, text="Bộ ký tự:").pack(anchor="w", padx=10, pady=5)
    for key, (chars, var) in char_set_options.items():
        Checkbutton(root, text=key, variable=var).pack(anchor="w", padx=20)

    Label(root, text="Số tiến trình:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=process_var).pack(anchor="w", padx=10)

    # Nút bắt đầu
    status_label = Label(root, text="Chưa bắt đầu.")
    status_label.pack(pady=10)

    def validate_and_start():
        if not os.path.isfile(zip_file_var.get()):
            messagebox.showerror("Lỗi", "Tệp ZIP không tồn tại.")
            return
        if max_length_var.get() <= 0:
            messagebox.showerror("Lỗi", "Độ dài mật khẩu phải lớn hơn 0.")
            return

        # Kết hợp bộ ký tự từ các lựa chọn
        final_char_set = "".join(chars for chars, var in char_set_options.values() if var.get())
        if not final_char_set:
            messagebox.showerror("Lỗi", "Bạn phải chọn ít nhất một bộ ký tự.")
            return

        settings = {
            "zip_file": zip_file_var.get(),
            "max_password_length": max_length_var.get(),
            "character_set": final_char_set,
            "max_processes": process_var.get()
        }

        # Kiểm tra tính hợp lệ của tiến trình đã lưu
        if not _validate_progress(settings):
            return

        threading.Thread(target=start_cracking_gui, args=(settings, progress_var, status_label)).start()

    Button(root, text="Bắt đầu giải mã", command=validate_and_start).pack(pady=10)

    # Thanh tiến trình
    ttk.Progressbar(root, variable=progress_var, maximum=100).pack(fill="x", padx=10, pady=10)

    root.mainloop()


if __name__ == "__main__":
    main_gui()
