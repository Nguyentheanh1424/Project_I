from tkinter import *
from tkinter import ttk, filedialog, messagebox
import multiprocessing
import threading
import os
from config import PROGRESS_FILE
from progress_manager import ProgressManager
from zip_cracker import ZipCracker

class ZipCrackerGUI:
    def __init__(self):
        self.root = Tk()
        self.widgets = []
        self.zip_file_var = StringVar(value="Nguyễn Thế Anh dz")
        self.max_length_var = IntVar()
        self.process_var = IntVar()
        self.progress_var = IntVar()

        self.setup_window()
        self.create_widgets()

    def setup_window(self):
        self.root.title("Giải Mã ZIP")
        self.root.geometry("300x450")
        self.root.resizable(False, False)

    def create_widgets(self):
        self._create_zip_file_section()
        self._create_password_length_section()
        self._create_charset_section()
        self._create_process_section()
        self._create_status_section()
        self._create_progress_bar()

    def _create_zip_file_section(self):
        Label(self.root, text="Tệp ZIP:").pack(anchor="w", padx=10, pady=5)
        zip_file_entry = Entry(self.root, textvariable=self.zip_file_var, width=50)
        zip_file_entry.pack(anchor="w", padx=10)
        self.widgets.append(zip_file_entry)

        zip_file_button = Button(
            self.root,
            text="Chọn tệp ZIP",
            command=lambda: self.zip_file_var.set(
                filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")])
            )
        )
        zip_file_button.pack(anchor="w", padx=10)
        self.widgets.append(zip_file_button)

    def _create_password_length_section(self):
        Label(self.root, text="Độ dài mật khẩu tối đa:").pack(anchor="w", padx=10, pady=5)
        max_length_entry = Entry(self.root, textvariable=self.max_length_var, width=50)
        max_length_entry.pack(anchor="w", padx=10)
        self.widgets.append(max_length_entry)

    def _create_charset_section(self):
        Label(self.root, text="Bộ ký tự:").pack(anchor="w", padx=10, pady=5)
        char_set_frame = ttk.Frame(self.root)
        char_set_frame.pack(anchor="w", padx=50)

        self.char_set_options = {
            "Lowercase": ("abcdefghijklmnopqrstuvwxyz", BooleanVar(value=True)),
            "Uppercase": ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", BooleanVar(value=False)),
            "Digits": ("0123456789", BooleanVar(value=True)),
            "Special": ("!@#$%^&*()-_=+[]{}|;:',.<>?/`~", BooleanVar(value=False)),
        }

        row, col = 0, 0
        for key, (chars, var) in self.char_set_options.items():
            cb = Checkbutton(char_set_frame, text=key, variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)
            self.widgets.append(cb)
            col += 1
            if col > 1:
                col = 0
                row += 1

    def _create_process_section(self):
        number_of_processes = multiprocessing.cpu_count()
        Label(self.root, 
              text=f"Số tiến trình: (1-{number_of_processes})").pack(anchor="w", padx=10, pady=5)
        process_entry = Entry(self.root, textvariable=self.process_var, width=50)
        process_entry.pack(anchor="w", padx=10)
        self.widgets.append(process_entry)

    def _create_status_section(self):
        self.status_label = Label(self.root, text="Nguyễn Thế Anh 20225163")
        self.status_label.pack(pady=10)

        self.start_button = Button(self.root, text="Thám mã", command=self._validate_and_start)
        self.start_button.pack(pady=10)
        self.widgets.append(self.start_button)

    def _create_progress_bar(self):
        self.progress_bar = ttk.Progressbar(
            self.root, 
            variable=self.progress_var, 
            maximum=100
        )
        self.progress_bar.pack(fill="x", padx=10, pady=10)

    def _enable_widgets(self):
        for widget in self.widgets:
            widget.config(state="normal")

    def _disable_widgets(self):
        for widget in self.widgets:
            widget.config(state="disable")

    def _validate_settings(self):
        if not os.path.isfile(self.zip_file_var.get()):
            messagebox.showerror("Lỗi", "Tệp ZIP không tồn tại.")
            return False

        try:

            max_length = self.max_length_var.get()
            if max_length <= 0:
                raise ValueError("Độ dài mật khẩu phải lớn hơn 0.")
        except ValueError as e:
            messagebox.showerror("Lỗi", str(e))
            return False
        except TclError:
            messagebox.showerror("Lỗi", "Vui lòng nhập độ dài mật khẩu hợp lệ.")
            return False

        final_char_set = "".join(
            chars for chars, var in self.char_set_options.values() 
            if var.get()
        )
        if not final_char_set:
            messagebox.showerror("Lỗi", "Bạn phải chọn ít nhất một bộ ký tự.")
            return False

        try:
            process_count = self.process_var.get()
            if process_count <= 0:
                raise ValueError("Số tiến trình phải lớn hơn 0.")
            if process_count > multiprocessing.cpu_count():
                raise ValueError(
                    f"Số tiến trình không được vượt quá số lõi CPU ({multiprocessing.cpu_count()})."
                )
        except ValueError as e:
            messagebox.showerror("Lỗi", str(e))
            return False
        except TclError:
            messagebox.showerror("Lỗi", "Vui lòng nhập độ dài mật khẩu hợp lệ.")
            return False

        return True

    def _get_settings(self):
        return {
            "zip_file": self.zip_file_var.get(),
            "max_password_length": self.max_length_var.get(),
            "character_set": "".join(
                chars for chars, var in self.char_set_options.values() 
                if var.get()
            ),
            "process_var": self.process_var.get()
        }


    def _validate_and_start(self):
        if not self._validate_settings():
            return

        settings = self._get_settings()
        self._disable_widgets()

        progress_manager = ProgressManager(PROGRESS_FILE)
        zip_cracker = ZipCracker(settings, progress_manager)

        def cracking_thread():
            zip_cracker.start_cracking(
                self.progress_var,
                progress_manager.validate_progress(settings),
                self.status_label
            )
            self._enable_widgets()

        threading.Thread(target=cracking_thread, daemon=True).start()

    def run(self):
        self.root.mainloop()
