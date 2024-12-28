import time
from multiprocessing import Process, Manager, Value
from tkinter import messagebox
import psutil
import pyzipper
from progress_manager import ProgressManager

class Cracker:
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.settings = self.progress_manager.settings
        self.smallest_file = None
        self.pause_flag = Value('i', 0)
        self.current_min_index = Value('i', 2 ** 31 - 1)

    def cracker(self, zf, charset, length, index):
        try:
            password = ""
            base = len(charset)
            for _ in range(length):
                password = charset[index % base] + password
                index //= base

            zf.setpassword(password.encode('utf-8'))
            if self.smallest_file:
                zf.extract(self.smallest_file)
                return password
        except (RuntimeError, pyzipper.BadZipFile, Exception):
            return None

    def bf_for_each_process(self, id_process, total_combinations, stop_flag, start_index, start_time, zip_path):
        charset = self.settings["charset"]
        p = psutil.Process()
        p.cpu_affinity([id_process % self.settings["number_workers"]])

        with pyzipper.AESZipFile(zip_path, 'r') as zf:
            for i in range(id_process + start_index, total_combinations, self.settings["number_workers"]):
                if stop_flag.value:
                    return
                if self.pause_flag.value:
                    with self.current_min_index.get_lock():
                        self.current_min_index.value = min(self.current_min_index.value, i)
                    while self.pause_flag.value:
                        time.sleep(0.1)
                result = self.cracker(zf, charset, self.settings["current_length"], i)
                if result:
                    stop_flag.value = 1
                    messagebox.showinfo(
                        "Success",
                        f"Password: {result}, cracking time: {time.time() - start_time:.2f} seconds")
                    self.progress_manager.delete_progress()
                    return

    def brute_force(self):
        start_time = time.time()
        charset = self.settings["charset"]
        stop_flag = Value('i', 0)

        with pyzipper.AESZipFile(self.settings["zip_path"], 'r') as zf:
            min_size = float('inf')
            for file in zf.namelist():
                file_info = zf.getinfo(file)
                if file_info.file_size < min_size:
                    min_size = file_info.file_size
                    self.smallest_file = file

        for password_length in range(self.settings["current_length"], self.settings["max_length"] + 1):
            self.settings["current_length"] = password_length
            total_combinations = len(charset) ** password_length

            processes = []
            for id_process in range(self.settings["number_workers"]):
                p = Process(target=self.bf_for_each_process,
                            args=(id_process, total_combinations, stop_flag, self.settings["current_index"], start_time, self.settings["zip_path"]))
                processes.append(p)
                p.start()

            for p in processes:
                p.join()

            if stop_flag.value:
                return

        messagebox.showinfo(
            "Unsuccessful",
            f"Password not found, cracking time: {time.time() - start_time:.2f} seconds")
        self.progress_manager.delete_progress()

    def dictionary_attack(self):
        start_time = time.time()
        wordlist_path = self.settings["wordlist_path"]
        zip_path = self.settings["zip_path"]
        number_workers = self.settings["number_workers"]

        # Xác định file nhỏ nhất trong tệp ZIP
        with pyzipper.AESZipFile(zip_path, 'r') as zf:
            min_size = float('inf')
            for file in zf.namelist():
                file_info = zf.getinfo(file)
                if file_info.file_size < min_size:
                    min_size = file_info.file_size
                    self.smallest_file = file

        try:
            with Manager() as manager:
                stop_flag = manager.Value('i', 0)
                found_password = manager.Value('s', '')
                processes = []

                for index_worker in range(number_workers):
                    p = Process(
                        target=self.dt_for_each_process,
                        args=(zip_path, wordlist_path, stop_flag, index_worker, number_workers, self.smallest_file, found_password)
                    )
                    processes.append(p)
                    p.start()

                for p in processes:
                    p.join()

                if stop_flag.value:
                    messagebox.showinfo(
                        "Success",
                        f"Password: {found_password.value}, cracking time: {time.time() - start_time:.2f} seconds"
                    )
                else:
                    messagebox.showinfo(
                        "Unsuccessful",
                        f"Password not found, cracking time: {time.time() - start_time:.2f} seconds"
                    )

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    @staticmethod
    def dt_for_each_process(zip_path, wordlist_path, stop_flag, index_worker, number_worker, smallest_file, found_password):
        p = psutil.Process()
        p.cpu_affinity([index_worker % number_worker])
        with pyzipper.AESZipFile(zip_path, 'r') as zf:
            try:
                with open(wordlist_path, 'r', encoding='utf-8') as file:
                    for index, line in enumerate(file):
                        if stop_flag.value:
                            break

                        if (index - index_worker) % number_worker == 0 and index >= index_worker:
                            password = line.strip()

                            zf.setpassword(password.encode('utf-8'))
                            try:
                                if smallest_file:
                                    zf.extract(smallest_file)
                                    stop_flag.value = 1
                                    found_password.value = password  # Lưu mật khẩu tìm được
                                    return
                            except (RuntimeError, pyzipper.BadZipFile, Exception):
                                continue
            except Exception as e:
                print(f"Error processing wordlist: {e}")
