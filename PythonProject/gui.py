import os
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from threading import Thread

from cracker import Cracker


class GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZIP Password Cracker")
        self.root.geometry("550x500")
        self.root.resizable(False, False)

        # Styling
        self.style = ttk.Style()
        self.style.configure("TButton", padding=5)
        self.style.configure("Header.TLabel", font=("Arial", 12, "bold"))

        self.cracker = Cracker()
        self.settings = self.cracker.progress_manager.settings

        # Create main frame with padding
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        self.components_to_disable = []

        self.setup_gui()
        self.toggle_mode()

    def setup_gui(self):
        # Header
        header = ttk.Label(self.main_frame, text="ZIP Password Recovery Tool", style="Header.TLabel")
        header.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # File Selection Frame
        file_frame = ttk.LabelFrame(self.main_frame, text="File Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(file_frame, text="ZIP File:").grid(row=0, column=0, sticky="w")
        self.zip_entry = ttk.Entry(file_frame, width=50)
        self.zip_entry.grid(row=0, column=1, padx=5)
        browse_zip_btn  = ttk.Button(file_frame, text="Browse", command=self.choose_zip)
        browse_zip_btn.grid(row=0, column=2)

        # Attack Mode Frame
        attack_frame = ttk.LabelFrame(self.main_frame, text="Attack Configuration", padding="10")
        attack_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(attack_frame, text="Mode:").grid(row=0, column=0, sticky="w")
        self.mode_var = tk.StringVar(value="Brute Force")
        modes = ["Brute Force", "Dictionary Attack"]
        mode_combo = ttk.Combobox(attack_frame, textvariable=self.mode_var, values=modes, state="readonly")
        mode_combo.grid(row=0, column=1, sticky="w", padx=5)
        mode_combo.bind('<<ComboboxSelected>>', lambda e: self.toggle_mode())

        # Brute Force Options
        self.bf_frame = ttk.Frame(attack_frame)
        self.bf_frame.grid(row=1, column=0, columnspan=3, pady=10)

        ttk.Label(self.bf_frame, text="Max Length:").grid(row=0, column=0, sticky="w")
        self.max_length_entry = ttk.Entry(self.bf_frame, width=10, justify="center")
        self.max_length_entry.grid(row=0, column=1, padx=5)
        self.max_length_entry.insert(0, "3")

        ttk.Label(self.bf_frame, text="Character Set:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.charset_entry = ttk.Entry(self.bf_frame, width=40)
        self.charset_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=(5, 0))
        (ttk.Label(self.bf_frame, text="Example: Lowercase+Uppercase+Digits+Special")
            .grid(row=2, column=1, columnspan=2, sticky="w"))
        self.charset_entry.insert(0, "lowercase + digits")

        # Dictionary Attack Options
        self.dict_frame = ttk.Frame(attack_frame)
        self.dict_frame.grid(row=2, column=0, columnspan=3, pady=10)

        ttk.Label(self.dict_frame, text="Wordlist:").grid(row=0, column=0, sticky="w")
        self.wordlist_entry = ttk.Entry(self.dict_frame, width=50)
        self.wordlist_entry.grid(row=0, column=1, padx=5)
        browse_wordlist_btn = (ttk.Button(self.dict_frame, text="Browse", command=self.choose_wordlist))
        browse_wordlist_btn .grid(row=0, column=2)

        # Process Configuration
        process_frame = ttk.LabelFrame(self.main_frame, text="Process Settings", padding="10")
        process_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        ttk.Label(process_frame, text=f"Number of Workers (1-{os.cpu_count() - 2}):").grid(row=0, column=0, sticky="w")
        self.workers_entry = ttk.Entry(process_frame, width=10, justify="center")
        self.workers_entry.grid(row=0, column=1, sticky="w", padx=5)
        self.workers_entry.insert(0, "4")

        # Status Frame
        status_frame = ttk.Frame(self.main_frame)
        status_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        self.status_label = ttk.Label(status_frame, text="Ready", foreground="green")
        self.status_label.pack(side="top", pady=5)

        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=400)
        self.progress.pack(side="top", pady=5)

        # Control Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=(0, 10))

        self.start_button = ttk.Button(button_frame, text="Start Attack", command=self.start_attack)
        self.start_button.pack(side="left", padx=5)

        self.pause_button = ttk.Button(button_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=5)
        self.pause_button.configure(state="disabled")

        ttk.Button(button_frame, text="Exit", command=self.root.destroy).pack(side="left", padx=5)

        self.components_to_disable.append(browse_zip_btn)
        self.components_to_disable.append(self.zip_entry)
        self.components_to_disable.append(mode_combo)
        self.components_to_disable.append(self.max_length_entry)
        self.components_to_disable.append(self.charset_entry)
        self.components_to_disable.append(browse_wordlist_btn)
        self.components_to_disable.append(self.wordlist_entry)
        self.components_to_disable.append(self.workers_entry)
        self.components_to_disable.append(self.start_button)
        self.components_to_disable.append(self.start_button)
        self.components_to_disable.extend([self.pause_button])

        self.is_paused = False

    def disable_components(self):
        for component in self.components_to_disable:
            component.configure(state="disabled")

    def enable_components(self):
        for component in self.components_to_disable:
            component.configure(state="normal")

    def toggle_pause(self):
        if not self.is_paused:
            # Tạm dừng
            self.cracker.pause_flag.value = 1
            self.is_paused = True
            self.pause_button.configure(text="Resume")
            self.status_label.config(text="Attack paused", foreground="orange")
            self.progress.stop()
            time.sleep(1)
            self.cracker.progress_manager.save_progress(self.cracker.current_min_index.value)
        else:
            # Tiếp tục
            self.cracker.pause_flag.value = 0
            self.is_paused = False
            self.pause_button.configure(text="Pause")
            self.status_label.config(text="Attack in progress."
                                          "..", foreground="orange")
            self.progress.start(interval=100)

    def toggle_mode(self):
        if self.mode_var.get() == "Brute Force":
            self.bf_frame.grid()
            self.dict_frame.grid_remove()
        else:
            self.bf_frame.grid_remove()
            self.dict_frame.grid()

    def choose_zip(self):
        zip_path = filedialog.askopenfilename(
            title="Select ZIP file",
            filetypes=[("ZIP Files", "*.zip"), ("All Files", "*.*")]
        )
        if zip_path:
            self.zip_entry.delete(0, tk.END)
            self.zip_entry.insert(0, zip_path)

    def choose_wordlist(self):
        wordlist_path = filedialog.askopenfilename(
            title="Select Wordlist",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if wordlist_path:
            self.wordlist_entry.delete(0, tk.END)
            self.wordlist_entry.insert(0, wordlist_path)

    def start_attack(self):
        # Validate inputs
        if not self.validate_inputs():
            return

        self.disable_components()
        self.pause_button.configure(state="normal")

        # Update status and UI
        self.status_label.config(text="Attack in progress...", foreground="orange")
        self.progress.start(interval=100)
        Thread(target=self.run_attack).start()

    def validate_inputs(self):
        zip_path = self.zip_entry.get().strip()
        if not zip_path:
            messagebox.showerror("Error", "Please select a ZIP file.")
            return False

        if not os.path.exists(zip_path):
            messagebox.showerror("Error", "File ZIP does not exist ")
            return False

        try:
            workers = int(self.workers_entry.get().strip())
            if not 1 <= workers <= os.cpu_count() - 2:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", f"Workers must be between 1 and {os.cpu_count() - 2}.")
            return False

        mode = self.mode_var.get()
        if mode == "Brute Force":
            try:
                try:
                    max_length = int(self.max_length_entry.get().strip())
                    if max_length <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Error", "Invalid maximum length")
                    return False
                charset = self.parse_charset(self.charset_entry.get().strip())
                if not charset:
                    raise ValueError("Invalid charset")
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid Brute Force parameters: {str(e)}")
                return False
        else:
            if not self.wordlist_entry.get().strip():
                messagebox.showerror("Error", "Please select a wordlist file.")
                return False
            if not os.path.exists(self.wordlist_entry.get().strip()):
                messagebox.showerror("Error", "Wordlist file does not exist.")
                return False

        return True

    def parse_charset(self, charset_input):
        if not charset_input:
            return ""

        charset = ""
        charset_map = {
            "lowercase": "abcdefghijklmnopqrstuvwxyz",
            "uppercase": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            "digits": "0123456789",
            "special": "!@#$%^&*()_+-=[]{}|;:'\",.<>?/"
        }

        for item in charset_input.split('+'):
            item = item.strip()
            if item.lower() in charset_map:
                charset += charset_map[item]
            else:
                charset += item

        return charset

    def run_attack(self):
        try:
            self.settings.update({
                "mode": self.mode_var.get(),
                "zip_path": self.zip_entry.get().strip(),
                "charset": self.parse_charset(
                    self.charset_entry.get().strip()) if self.mode_var.get() == "Brute Force" else None,
                "number_workers": int(self.workers_entry.get().strip()),
                "max_length": int(self.max_length_entry.get().strip()) if self.mode_var.get() == "Brute Force" else 0,
                "current_length": 1,
                "current_index": 0,
                "wordlist_path": self.wordlist_entry.get().strip() if self.mode_var.get() == "Dictionary Attack" else None
            })

            if self.mode_var.get() == "Brute Force":
                progress = self.cracker.progress_manager.load_progress("Brute Force")
                if not progress:
                    self.settings.update({
                        "zip_path": self.zip_entry.get().strip(),
                        "mode": self.mode_var.get(),
                        "number_workers": int(self.workers_entry.get().strip()),
                        "max_length": int(self.max_length_entry.get().strip()),
                        "charset": self.parse_charset(self.charset_entry.get().strip()),
                        "current_length": 1,
                        "current_index": 0
                    })
                else: self.settings = progress
                self.cracker.brute_force()

            else:
                progress = self.cracker.progress_manager.load_progress("Dictionary Attack")
                if not progress:
                    self.settings.update({
                        "zip_path": self.zip_entry.get().strip(),
                        "mode": self.mode_var.get(),
                        "wordlist_path": self.wordlist_entry.get().strip(),
                    })
                else:
                    self.settings = progress
                self.cracker.dictionary_attack()

            self.status_label.config(text="Attack completed!", foreground="green")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
        finally:
            self.progress.stop()
            self.enable_components()
            # Disable pause button và reset trạng thái
            self.pause_button.configure(state="disabled", text="Pause")
            self.is_paused = False
            self.cracker.pause_flag.value = 0

if __name__ == "__main__":
    root = tk.Tk()
    gui = GUI(root)
    root.mainloop()