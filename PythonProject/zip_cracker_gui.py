from tkinter import *
from tkinter import ttk, filedialog, messagebox
import multiprocessing
import threading
import os

from cracker import BruteForce, DictionaryAttacker
from config import PROGRESS_FILE
from progress_manager import ProgressManager


class ZipCrackerGUI:
    def __init__(self):
        # Khởi tạo cửa sổ chính của ứng dụng
        self.root = Tk()

        # Danh sách lưu các widget để quản lý trạng thái enable/disable
        self.widgets = []

        # Khởi tạo các biến trong giao diện
        self.zip_file_var = StringVar(value="Nguyễn Thế Anh 20225163")  # Đường dẫn file ZIP
        self.max_length_var = IntVar()  # Độ dài tối đa của mật khẩu
        self.process_var = IntVar()  # Số lượng process sử dụng
        self.progress_var = IntVar()  # Thanh tiến trình hiện tại (0-100)%

        self.char_set_options = {
            "Lowercase": ("abcdefghijklmnopqrstuvwxyz", BooleanVar(value=True)),
            "Uppercase": ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", BooleanVar(value=False)),
            "Digits": ("0123456789", BooleanVar(value=True)),
            "Special": ("!@#$%^&*()-_=+[]{}|;:',.<>?/~", BooleanVar(value=False)),
            "Custom": ("", BooleanVar(value=False)),
        }

        # Thiết lập cửa sổ và tạo các widget
        self.setup_window()
        self.create_widgets()

    def setup_window(self):
        # Cấu hình cửa sổ chính với kích thước cố định
        self.root.title("Giải Mã ZIP")
        self.root.geometry("300x600")
        self.root.resizable(False, False)

    def create_widgets(self):
        # Tạo các phần giao diện theo thứ tự
        self._create_zip_file_section()             # Phần chọn file ZIP
        self._create_attack_mode_section()          # Phần chọn chế độ tấn công
        self._create_password_length_section()      # Phần nhập độ dài mật khẩu
        self._create_charset_section()              # Phần chọn bộ ký tự
        self._create_custom_charset_section()       # Phần nhập ký tự tùy chỉnh
        self._create_process_section()              # Phần chọn số tiến trình
        self._create_status_section()               # Phần hiển thị trạng thái
        self._create_progress_bar()                 # Thanh tiến trình

    def _create_zip_file_section(self):
        # Tạo label cho phần chọn file ZIP
        Label(self.root, text="Tệp ZIP:").pack(anchor="w", padx=10, pady=5)

        # Tạo ô nhập liệu đường dẫn file ZIP
        zip_file_entry = Entry(self.root, textvariable=self.zip_file_var, width=50)
        zip_file_entry.pack(anchor="w", padx=10, pady=5)
        self.widgets.append(zip_file_entry)

        # Tạo nút "Chọn tệp ZIP" để mở dialog chọn file
        zip_file_button = Button(
            self.root,
            text="Chọn tệp ZIP",
            command=lambda: self.zip_file_var.set(
                filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")])
            )
        )
        zip_file_button.pack(anchor="w", padx=10, pady=5)
        self.widgets.append(zip_file_button)

    def _create_attack_mode_section(self):
        Label(self.root, text="Chế độ tấn công:").pack(anchor="w", padx=10, pady=5)
        self.attack_mode = StringVar(value="Brute Force")

        modes_frame = ttk.Frame(self.root)
        modes_frame.pack(anchor="w", padx=50)

        Radiobutton(
            modes_frame, text="Brute Force",
            variable=self.attack_mode,
            value="Brute Force",
            command=self._toggle_attack_mode
        ).pack(anchor="w")

        Radiobutton(
            modes_frame, text="Dictionary Attack",
            variable=self.attack_mode,
            value="Dictionary Attack",
            command=self._toggle_attack_mode
        ).pack(anchor="w")

        # Thêm frame cho Dictionary Attack
        self.dict_frame = ttk.Frame(self.root)
        self.wordlist_path = StringVar()

        # Wordlist label và entry
        Label(self.dict_frame, text="Wordlist:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        wordlist_entry = Entry(self.dict_frame, textvariable=self.wordlist_path, width=50)
        wordlist_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        # Nút chọn Wordlist
        Button(
            self.dict_frame, text="Chọn Wordlist",
            command=self._select_wordlist
        ).grid(row=1, column=1, sticky="w", padx=10, pady=5)

    def _toggle_attack_mode(self):
        # Điều chỉnh giao diện cho chế độ Dictionary Attack
        if self.attack_mode.get() == "Dictionary Attack":
            self.root.geometry("300x450")
            if not self.dict_frame.winfo_ismapped():
                self.dict_frame.pack(after=self.password_length_frame, anchor="w", padx=10, pady=5)

            # Ẩn giao diện liên quan đến Brute Force
            if self.password_length_label.winfo_ismapped():
                self.password_length_label.pack_forget()
            if self.password_length_frame.winfo_ismapped():
                self.password_length_frame.pack_forget()
            if self.charset_frame.winfo_ismapped():
                self.charset_frame.pack_forget()
            if self.custom_charset_frame.winfo_ismapped():
                self.custom_charset_frame.pack_forget()
            if self.charset_label.winfo_ismapped():
                self.charset_label.pack_forget()
        else:
            # Điều chỉnh giao diện cho chế độ Brute Force
            self._clear_widgets()
            self.root.geometry("300x600")
            self.create_widgets()

    def _select_wordlist(self):
        filename = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if filename:
            self.wordlist_path.set(filename)

    def _create_password_length_section(self):
        self.password_length_label = Label(self.root, text="Độ dài mật khẩu tối đa:")
        self.password_length_label.pack(anchor="w", padx=10, pady=5)

        self.password_length_frame = Entry(self.root, textvariable=self.max_length_var, width=50)
        self.password_length_frame.pack(anchor="w", padx=10)

        self.widgets.append(self.password_length_label)
        self.widgets.append(self.password_length_frame)

    def _create_charset_section(self):
        self.charset_label = Label(self.root, text="Bộ ký tự:")
        self.charset_label.pack(anchor="w", padx=10, pady=5)
        self.charset_frame = ttk.Frame(self.root)
        self.charset_frame.pack(anchor="w", padx=50)

        row, col = 0, 0
        for key, (chars, var) in self.char_set_options.items():
            cb = Checkbutton(self.charset_frame, text=key, variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=10, pady=2)
            self.widgets.append(cb)
            col += 1
            if col > 1:
                col = 0
                row += 1

    def _create_custom_charset_section(self):
        self.custom_charset_frame = ttk.Frame(self.root)
        Label(self.custom_charset_frame, text="Ký tự tùy chỉnh:").pack(anchor="w", pady=5)
        self.custom_charset_var = StringVar()
        custom_charset_entry = Entry(self.custom_charset_frame, textvariable=self.custom_charset_var, width=50)
        custom_charset_entry.pack(anchor="w")
        self.widgets.append(custom_charset_entry)
        self.custom_charset_frame.pack(anchor="w", padx=10, pady=5)

    def _create_process_section(self):
        number_of_processes = multiprocessing.cpu_count()
        Label(self.root, text=f"Số tiến trình: (1-{number_of_processes})").pack(anchor="w", padx=10, pady=5)
        process_entry = Entry(self.root, textvariable=self.process_var, width=50)
        process_entry.pack(anchor="w", padx=10)
        self.widgets.append(process_entry)

    def _create_status_section(self):
        self.status_label = Label(self.root, text="Đang chờ hoạt động")
        self.status_label.pack(pady=10)

        self.start_button = Button(self.root, text="Thám mã", command=self._validate_and_start)
        self.start_button.pack(pady=10)
        self.widgets.append(self.start_button)

    def _create_progress_bar(self):
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", padx=10, pady=10)

    def _clear_widgets(self):
        for widget in self.root.winfo_children():
            widget.destroy()

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

        charset = ""
        for key, (chars, var) in self.char_set_options.items():
            if var.get():
                if key == "Custom":
                    custom_chars = self.custom_charset_var.get()
                    if not custom_chars and self.char_set_options["Custom"][1].get():
                        messagebox.showerror("Lỗi", "Vui lòng nhập ký tự tùy chỉnh hoặc bỏ chọn tùy chọn Custom.")
                        return False
                    charset += custom_chars
                else:
                    charset += chars

        if not charset:
            messagebox.showerror("Lỗi", "Bạn phải chọn ít nhất một bộ ký tự.")
            return False

        try:
            process_count = self.process_var.get()
            if process_count <= 0:
                raise ValueError("Số tiến trình phải lớn hơn 0.")
            if process_count > multiprocessing.cpu_count():
                raise ValueError(f"Số tiến trình không được vượt quá số lõi CPU ({multiprocessing.cpu_count()}).")
        except ValueError as e:
            messagebox.showerror("Lỗi", str(e))
            return False
        except TclError:
            messagebox.showerror("Lỗi", "Vui lòng nhập độ dài mật khẩu hợp lệ.")
            return False

        return True

    def _get_settings(self):
        charset = ""
        for key, (chars, var) in self.char_set_options.items():
            if var.get():
                if key == "Custom":
                    custom_chars = self.custom_charset_var.get()
                    if custom_chars:
                        charset += custom_chars
                else:
                    charset += chars

        return {
            "zip_file": self.zip_file_var.get(),
            "max_password_length": self.max_length_var.get(),
            "character_set": charset,
            "process_var": self.process_var.get()
        }

    def _validate_and_start(self):
        if not self._validate_settings():
            return

        settings = self._get_settings()
        self._disable_widgets()

        try:
            if self.attack_mode.get() == "Brute Force":
                self._start_brute_force(settings)
            elif self.attack_mode.get() == "Dictionary Attack":
                self._start_dictionary_attack()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không xác định: {e}")
            self._enable_widgets()

    def _start_brute_force(self, settings):
        """Khởi động tấn công brute force."""
        progress_manager = ProgressManager(PROGRESS_FILE)
        brute_force = BruteForce(settings, progress_manager)

        self._start_attack(
            attack_method=brute_force.start_cracking,
            progress_manager=progress_manager,
            settings=settings,
            validate_progress=True
        )

    def _start_dictionary_attack(self):
        """Khởi động tấn công dictionary attack."""
        if not os.path.isfile(self.wordlist_path.get()):
            messagebox.showerror("Lỗi", "Vui lòng chọn File Wordlist hợp lệ")
            return

        progress_manager = ProgressManager(PROGRESS_FILE)
        dictionary_attacker = DictionaryAttacker(
            {
                "zip_file": self.zip_file_var.get(),
                "process_var": self.process_var.get()
            },
            progress_manager
        )

        self._start_attack(
            attack_method=dictionary_attacker.start_cracking,
            progress_manager=progress_manager,
            wordlist_path=self.wordlist_path.get()
        )

    def _start_attack(self, attack_method, progress_manager, settings=None, wordlist_path=None, validate_progress=False):
        """
        Hàm dùng chung để khởi động các kiểu tấn công.

        Args:
            attack_method: Hàm thực thi tấn công từ lớp tấn công (brute force/dictionary).
            progress_manager: Đối tượng quản lý tiến trình.
            settings: (dict) Cấu hình tấn công (chỉ dùng cho brute force).
            wordlist_path: (str) Đường dẫn wordlist (chỉ dùng cho dictionary attack).
            validate_progress: (bool) Có xác nhận tiến trình trước đó không.
        """
        def cracking_thread():
            try:
                if settings and validate_progress:
                    attack_method(
                        self.progress_var,
                        progress_manager.validate_progress(settings),
                        self.status_label
                    )
                elif wordlist_path:
                    attack_method(
                        wordlist_path,
                        self.progress_var,
                        self.status_label
                    )
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi trong quá trình tấn công: {e}")
            finally:
                self._enable_widgets()

        threading.Thread(target=cracking_thread, daemon=True).start()

    def update_progress(self):
        """Cập nhật tiến trình thanh tiến trình."""
        self.progress_bar["value"] = self.progress_var.get()
        if self.progress_var.get() < 100:
            self.root.after(50, self.update_progress)


    def run(self):
        self.update_progress()
        self.root.mainloop()