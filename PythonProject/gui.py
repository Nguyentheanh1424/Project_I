from tkinter import *
from tkinter import filedialog, ttk, messagebox
import threading
from cracker import PasswordCracker
from utils import save_progress, load_progress, delete_progress

def main_gui():
    root = Tk()
    root.title("Giải Mã ZIP")
    root.geometry("300x450")
    root.resizable(False, False)

    zip_file_var = StringVar()
    max_length_var = IntVar(value=1)
    progress_var = IntVar(value=0)
    char_set_var = StringVar(value="abcdefghijklmnopqrstuvwxyz")

    Label(root, text="Tệp ZIP:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=zip_file_var, width=40).pack(anchor="w", padx=10)

    Button(root, text="Chọn tệp ZIP", command=lambda: zip_file_var.set(filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")]))).pack(anchor="w", padx=10)

    Label(root, text="Độ dài mật khẩu tối đa:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=max_length_var, width=40).pack(anchor="w", padx=10)

    Label(root, text="Bộ ký tự:").pack(anchor="w", padx=10, pady=5)
    Entry(root, textvariable=char_set_var, width=40).pack(anchor="w", padx=10)

    status_label = Label(root, text="Chưa bắt đầu.")
    status_label.pack(pady=10)

    def start_cracking():
        if not zip_file_var.get() or not max_length_var.get() > 0:
            messagebox.showerror("Lỗi", "Vui lòng nhập đúng thông tin.")
            return

        settings = {
            "zip_file": zip_file_var.get(),
            "max_password_length": max_length_var.get(),
            "character_set": char_set_var.get()
        }

        cracker = PasswordCracker(settings["zip_file"], settings["character_set"], settings["max_password_length"])

        if not cracker.validate_zip_file():
            messagebox.showerror("Lỗi", "Tệp ZIP không hợp lệ.")
            return

        def crack_thread():
            status_label.config(text="Đang chạy...")
            for length in range(1, settings["max_password_length"] + 1):
                total_combinations = len(settings["character_set"]) ** length
                for start in range(0, total_combinations, 1000):
                    passwords = cracker.generate_password_chunk(length, start, 1000)
                    for password in passwords:
                        result = cracker.crack_password(password)
                        if result:
                            messagebox.showinfo("Thành công", f"Mật khẩu là: {result}")
                            delete_progress()
                            status_label.config(text="Hoàn thành!")
                            return
            messagebox.showinfo("Kết thúc", "Không tìm thấy mật khẩu.")

        threading.Thread(target=crack_thread).start()

    Button(root, text="Bắt đầu", command=start_cracking).pack(pady=10)

    ttk.Progressbar(root, variable=progress_var, maximum=100).pack(fill="x", padx=10, pady=10)

    root.mainloop()
