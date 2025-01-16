import os
import time
import tkinter as tk
from tkinter import filedialog, ttk
from threading import Thread
from cracker import Cracker

class GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZIP Password Cracker")
        self.root.geometry("510x500")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.style = ttk.Style()
        self.style.configure("TButton", padding=5)
        self.style.configure("Header.TLabel", font=("Arial", 12, "bold"))

        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        self.zip_entry = None
        self.mode_var = None
        self.bf_frame = None
        self.max_length_entry = None
        self.charset_entry = None
        self.dict_frame = None
        self.wordlist_entry = None
        self.workers_entry = None
        self.status_label = None
        self.progress = None
        self.start_button = None
        self.pause_button = None
        self.is_paused = None
        self.should_update_progress = None
        self.update_thread = None

        self.components_to_disable = []
        self.is_paused = False

        self.setup_gui()
        self.toggle_mode()

        self.cracker = Cracker()
        self.settings = self.cracker.settings


    def exit_program(self):
        if hasattr(self.cracker, 'stop_flag'):
            self.cracker.stop_flag.value = 1
        self.root.destroy()


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

        # Progress bar
        self.progress = ttk.Progressbar(status_frame, mode="determinate", length=400)
        self.progress.pack(side="top", pady=5)

        # Control Buttons
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=(0, 10))

        self.start_button = ttk.Button(button_frame, text="Start Attack", command=self.start_attack)
        self.start_button.pack(side="left", padx=5)

        self.pause_button = ttk.Button(button_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=5)
        self.pause_button.configure(state="disabled")

        ttk.Button(button_frame, text="Exit", command=self.exit_program).pack(side="left", padx=5)

        self.components_to_disable.extend([
            browse_zip_btn, self.zip_entry, mode_combo,
            self.max_length_entry, self.charset_entry,
            browse_wordlist_btn, self.wordlist_entry,
            self.workers_entry, self.start_button,
            self.pause_button
        ])

    def start_progress_update(self):
        self.should_update_progress = True
        self.update_thread = Thread(target=self._update_progress_loop)
        self.update_thread.daemon = True
        self.update_thread.start()

    def stop_progress_update(self):
        self.should_update_progress = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=0.5)

    def _update_progress_loop(self):
        while self.should_update_progress:
            try:
                self._update_progress()
                time.sleep(0.5)
            except Exception as e:
                print(f"Error updating progress: {e}")
                break

    def _update_progress(self):
        if not hasattr(self.cracker, 'start_time') or not self.cracker.start_time:
            return

        try:
            current = self.cracker.passwords_tried.value
            total = self.cracker.total_password.value
            elapsed_time = time.time() - self.cracker.start_time

            if total > 0:
                percentage = min((current / total) * 100, 100)  # Ensure percentage doesn't exceed 100
                remaining = total - current

                if current > 0:
                    time_per_password = elapsed_time / current
                    estimated_remaining = time_per_password * remaining
                    hours_remaining = estimated_remaining // 3600
                    minutes_remaining = (estimated_remaining % 3600) // 60
                    seconds_remaining = estimated_remaining % 60

                    current_formatted = "{:,}".format(current)
                    total_formatted = "{:,}".format(total)

                    if not self.is_paused:
                        status_text = (
                            f"Progress: {current_formatted}/{total_formatted} ({percentage:.2f}%) - "
                            f"ETA: {int(hours_remaining)}h {int(minutes_remaining)}m {int(seconds_remaining)}s"
                        )
                    else:
                        status_text = f"Attack paused at {percentage:.2f}%"

                    self.status_label.config(text=status_text, foreground="orange")
                    self.progress["value"] = percentage
                else:
                    self.status_label.config(text="Calculating remaining time...", foreground="orange")
        except Exception as e:
            print(f"Error in _update_progress: {e}")


    def disable_components(self):
        for component in self.components_to_disable:
            component.configure(state="disabled")

    def enable_components(self):
        for component in self.components_to_disable:
            component.configure(state="normal")

    def toggle_pause(self):
        if not self.is_paused:
            self.cracker.pause_flag.value = 1
            self.is_paused = True
            self.pause_button.configure(text="Resume")
            self.status_label.config(text="Attack paused", foreground="orange")
            time.sleep(0.5)
            self.cracker.progress_manager.save_progress(self.cracker.current_min_index.value, self.cracker.passwords_tried.value)
        else:
            self.cracker.pause_flag.value = 0
            self.is_paused = False
            self.pause_button.configure(text="Pause")
            self.status_label.config(text="Attack in progress...", foreground="orange")

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
        self.disable_components()
        self.pause_button.configure(state="normal")
        self.status_label.config(text="Attack in progress...", foreground="orange")
        self.progress["value"] = 0

        Thread(target=self.run_attack).start()

        self.start_progress_update()


    @staticmethod
    def parse_charset(charset_input):
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
            # Validate input before starting
            if not self._validate_inputs():
                return

            self._configure_attack_settings()

            # Reset progress tracking
            self.cracker.passwords_tried.value = 0
            self.cracker.total_password.value = 0
            self.cracker.start_time = time.time()

            if self.mode_var.get() == "Brute Force":
                self._run_brute_force_attack()
            else:
                self._run_dictionary_attack()

        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", foreground="red")
            raise
        finally:
            self.stop_progress_update()
            self.enable_components()
            self.pause_button.configure(state="disabled", text="Pause")
            self.is_paused = False
            self.cracker.pause_flag.value = 0

    def _validate_inputs(self):
        # Validate ZIP file
        if not self.zip_entry.get().strip():
            self.status_label.config(text="Error: Please select a ZIP file", foreground="red")
            return False

        # Validate workers
        try:
            workers = int(self.workers_entry.get().strip())
            if workers < 1 or workers > os.cpu_count() - 2:
                raise ValueError
        except ValueError:
            self.status_label.config(
                text=f"Error: Workers must be between 1 and {os.cpu_count() - 2}",
                foreground="red"
            )
            return False

        if self.mode_var.get() == "Brute Force":
            # Validate max length
            try:
                max_length = int(self.max_length_entry.get().strip())
                if max_length < 1:
                    raise ValueError
            except ValueError:
                self.status_label.config(text="Error: Invalid maximum length", foreground="red")
                return False

            # Validate charset
            charset = self.parse_charset(self.charset_entry.get().strip())
            if not charset:
                self.status_label.config(text="Error: Invalid character set", foreground="red")
                return False
        else:
            # Validate wordlist
            if not self.wordlist_entry.get().strip():
                self.status_label.config(text="Error: Please select a wordlist file", foreground="red")
                return False

        return True



    def _configure_attack_settings(self):
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

    def _run_brute_force_attack(self):
        try:
            progress = self.cracker.progress_manager.load_progress(
                "Brute Force",
                charset=self.parse_charset(self.charset_entry.get().strip()),
                max_length=int(self.max_length_entry.get().strip())
            )

            if not progress:
                self.settings.update({
                    "zip_path": self.zip_entry.get().strip(),
                    "mode": self.mode_var.get(),
                    "number_workers": int(self.workers_entry.get().strip()),
                    "max_length": int(self.max_length_entry.get().strip()),
                    "charset": self.parse_charset(self.charset_entry.get().strip()),
                    "current_length": 1,
                    "current_index": 0,
                    "passwords_tried": 0
                })
            else:
                self.settings = progress

            self.cracker.brute_force(self.settings)
        except Exception as e:
            self.status_label.config(text=f"Error in brute force attack: {str(e)}", foreground="red")
            raise

    def _run_dictionary_attack(self):
        try:
            progress = self.cracker.progress_manager.load_progress(
                "Dictionary Attack",
                wordlist_path=self.wordlist_entry.get().strip()
            )

            if not progress:
                self.settings.update({
                    "zip_path": self.zip_entry.get().strip(),
                    "mode": self.mode_var.get(),
                    "number_workers": int(self.workers_entry.get().strip()),
                    "wordlist_path": self.wordlist_entry.get().strip(),
                    "current_index": 0,
                    "passwords_tried": 0
                })
            else:
                self.settings = progress

            self.cracker.dictionary_attack(self.settings)
        except Exception as e:
            self.status_label.config(text=f"Error in dictionary attack: {str(e)}", foreground="red")
            raise

    def on_closing(self):
        self.stop_progress_update()

        if hasattr(self, 'cracker'):
            if hasattr(self.cracker, 'stop_flag'):
                self.cracker.stop_flag.value = 1
            time.sleep(0.5)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GUI(root)
    root.mainloop()