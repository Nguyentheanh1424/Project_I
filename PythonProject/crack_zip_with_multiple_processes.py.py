import json
import logging
import multiprocessing
import os
import sys
import threading
from tkinter import Tk, Label, Entry, Button, StringVar, filedialog, IntVar, ttk, messagebox, BooleanVar, Checkbutton
import pyzipper
import concurrent.futures
import queue
import time

# Đặt mã hóa UTF-8 để hỗ trợ tiếng Việt
sys.stdout.reconfigure(encoding='utf-8')

PROGRESS_FILE = "progress.json"


def _save_progress(progress, settings, current_length, current_index):
    progress.update({
        "zip_file": settings["zip_file"],
        "max_password_length": settings["max_password_length"],
        "character_set": settings["character_set"],
        "current_length": current_length,
        "current_index": current_index
    })
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=4)
    except Exception as e:
        # messagebox.showerror("Lỗi", "Không lưu được tiến độ.")
        pass


def _load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            _delete_progress()
    return None


def _delete_progress():
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


# Kiểm tra tính hợp lệ của tiến trình đã lưu
def _validate_progress(settings):
    progress = _load_progress()
    if not progress:
        return False

    required_keys = ["zip_file", "max_password_length", "character_set", "current_length", "current_index"]
    if not all(key in progress for key in required_keys):
        return False

    if (progress["zip_file"] == settings["zip_file"] and
            progress["max_password_length"] == settings["max_password_length"] and
            progress["character_set"] == settings["character_set"] and
            progress["current_length"] != 0 and
            progress["current_index"] != 0):
        response = messagebox.askquestion("Tìm thấy tiến trình cũ", "Bạn có muốn tiếp tục thực hiện từ lần dừng trước không?.")
        if response == "yes":
            return True
        else:
            return False

    return False


def _generate_password_chunk(chars, length, start, chunk_size):
    total_combinations = len(chars) ** length
    end = min(start + chunk_size, total_combinations)
    for i in range(start, end):
        password = ""
        idx = i
        for _ in range(length):
            password = chars[idx % len(chars)] + password
            idx //= len(chars)
        yield password


def _crack_worker(zip_file, password, stop_flag, result_queue):
    if stop_flag.is_set():
        return
    try:
        with pyzipper.AESZipFile(zip_file, 'r') as zf:
            zf.extractall(pwd=password.encode('utf-8'))
        stop_flag.set()
        result_queue.put(password)
    except (RuntimeError, pyzipper.BadZipFile):
        return
    except Exception as e:
        pass


def run_stride_cracking(zip_file, passwords, stop_flag, num_processes):
    result_queue = multiprocessing.Manager().Queue()
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = [
            executor.submit(_crack_worker, zip_file, password, stop_flag, result_queue)
            for password in passwords
        ]
        for future in concurrent.futures.as_completed(futures):
            if not result_queue.empty():
                return result_queue.get()
    return None


def start_cracking(settings, progress_var, _validate_progress, status_label):
    zip_file = settings["zip_file"]
    char_set = settings["character_set"]
    max_length = settings["max_password_length"]
    process_var = settings["process_var"]
    chunk_size = 100 * process_var
    stop_flag = multiprocessing.Manager().Event()
    progress_queue = queue.Queue()

    if _validate_progress:
        progress = _load_progress()
    else:
        progress = {"current_length": 1, "current_index": 0}

    # Ghi lại thời gian bắt đầu
    start_time = time.time()

    def update_progress():
        while True:
            try:
                new_progress = progress_queue.get(timeout=1)
                progress_var.set(new_progress)
            except queue.Empty:
                if stop_flag.is_set():
                    break

    threading.Thread(target=update_progress, daemon=True).start()

    for length in range(progress["current_length"], max_length + 1):
        total_combinations = len(char_set) ** length
        status_label.config(text=f"Đang thử mật khẩu độ dài {length}...")

        for start in range(progress["current_index"], total_combinations, chunk_size):
            passwords = list(_generate_password_chunk(char_set, length, start, chunk_size))
            result = run_stride_cracking(zip_file, passwords, stop_flag, process_var)
            if result:
                end_time = time.time()  # Ghi lại thời gian kết thúc
                elapsed_time = end_time - start_time
                formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                status_label.config(
                    text=f"Mật khẩu đã giải mã thành công: {result}\nThời gian: {formatted_time}"
                )
                _delete_progress()
                progress_var.set(100)
                return

            _save_progress(progress, settings, length, start + chunk_size)
            progress_queue.put((start + chunk_size) / total_combinations * 100)

        progress["current_index"] = 0
        progress["current_length"] += 1
        progress_var.set(0)

    # Nếu không tìm thấy mật khẩu
    end_time = time.time()
    elapsed_time = end_time - start_time
    formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    status_label.config(text=f"Không tìm thấy mật khẩu.\nThời gian: {formatted_time}")
    progress_var.set(0)
    _delete_progress()


def main_gui():
    root = Tk()
    root.title("Giải Mã ZIP")
    root.geometry("300x450")
    root.resizable(False, False)

    zip_file_var = StringVar()
    max_length_var = IntVar(value=1)
    process_var = IntVar(value=multiprocessing.cpu_count())
    progress_var = IntVar(value=0)

    char_set_options = {
        "Lowercase": ("abcdefghijklmnopqrstuvwxyz", BooleanVar(value=True)),
        "Uppercase": ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", BooleanVar(value=False)),
        "Digits": ("0123456789", BooleanVar(value=True)),
        "Special": ("!@#$%^&*()-_=+[]{}|;:',.<>?/`~", BooleanVar(value=False)),
    }

    widgets = []

    # Tệp ZIP
    Label(root, text="Tệp ZIP:").pack(anchor="w", padx=10, pady=5)
    zip_file_entry = Entry(root, textvariable=zip_file_var, width=50)
    zip_file_entry.pack(anchor="w", padx=10)
    widgets.append(zip_file_entry)

    zip_file_button = Button(root, text="Chọn tệp ZIP",
                             command=lambda: zip_file_var.set(
                                 filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")])))
    zip_file_button.pack(anchor="w", padx=10)
    widgets.append(zip_file_button)

    # Độ dài mật khẩu
    Label(root, text="Độ dài mật khẩu tối đa:").pack(anchor="w", padx=10, pady=5)
    max_length_entry = Entry(root, textvariable=max_length_var, width=50)
    max_length_entry.pack(anchor="w", padx=10)
    widgets.append(max_length_entry)

    # Bộ ký tự
    Label(root, text="Bộ ký tự:").pack(anchor="w", padx=10, pady=5)
    char_set_frame = ttk.Frame(root)
    char_set_frame.pack(anchor="w", padx=50)

    row, col = 0, 0
    char_set_checkbuttons = []
    for key, (chars, var) in char_set_options.items():
        cb = Checkbutton(char_set_frame, text=key, variable=var)
        cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)
        char_set_checkbuttons.append(cb)
        col += 1
        if col > 1:
            col = 0
            row += 1

    widgets.extend(char_set_checkbuttons)

    # Số tiến trình
    Label(root, text="Số tiến trình:").pack(anchor="w", padx=10, pady=5)
    process_entry = Entry(root, textvariable=process_var, width=50)
    process_entry.pack(anchor="w", padx=10)
    widgets.append(process_entry)

    # Trạng thái
    status_label = Label(root, text="Chưa bắt đầu.")
    status_label.pack(pady=10)

    # Hàm bật/tắt widget
    def _enable_widgets():
        for widget in widgets:
            widget.config(state="normal")

    def _disable_widgets():
        for widget in widgets:
            widget.config(state="disable")

    # Nút bắt đầu
    def validate_and_start():
        if not os.path.isfile(zip_file_var.get()):
            messagebox.showerror("Lỗi", "Tệp ZIP không tồn tại.")
            return

        if max_length_var.get() <= 0:
            messagebox.showerror("Lỗi", "Độ dài mật khẩu phải lớn hơn 0.")
            return

        final_char_set = "".join(chars for chars, var in char_set_options.values() if var.get())
        if not final_char_set:
            messagebox.showerror("Lỗi", "Bạn phải chọn ít nhất một bộ ký tự.")
            return

        settings = {
            "zip_file": zip_file_var.get(),
            "max_password_length": max_length_var.get(),
            "character_set": final_char_set,
            "process_var": process_var.get()
        }

        _disable_widgets()

        def finish_callback():
            _enable_widgets()

        threading.Thread(
            target=lambda: (start_cracking(settings, progress_var, _validate_progress(settings), status_label),
                            finish_callback()),
            daemon=True
        ).start()

    start_button = Button(root, text="Thám mã", command=validate_and_start)
    start_button.pack(pady=10)
    widgets.append(start_button)

    ttk.Progressbar(root, variable=progress_var, maximum=100).pack(fill="x", padx=10, pady=10)

    root.mainloop()


if __name__ == "__main__":
    main_gui()
