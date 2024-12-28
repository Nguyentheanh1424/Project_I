import mmap
import os
import psutil
import pyzipper
import time
from multiprocessing import Process, Value, current_process, Pool
from tkinter import messagebox
from progress_manager import ProgressManager


def test_passwords_worker(args):
    zip_path, password_batch = args
    with pyzipper.AESZipFile(zip_path, 'r') as zf:
        for password in password_batch:
            if not password:
                continue
            try:
                zf.setpassword(password.encode('utf-8'))
                zf.extractall()
                return password
            except (RuntimeError, pyzipper.BadZipFile, Exception):
                continue
    return None


def process_chunk_worker(chunk_start, chunk_size, file_path, zip_path, process_id, stop_flag):

    p = psutil.Process()
    p.cpu_affinity([process_id % psutil.cpu_count()])

    try:
        with open(file_path, 'rb') as f:
            f.seek(chunk_start)
            chunk_data = f.read(chunk_size)

            passwords = chunk_data.decode('utf-8', errors='ignore').splitlines()
            batch_size = 50000

            for i in range(0, len(passwords), batch_size):
                if stop_flag.value:
                    return None

                batch = passwords[i:i + batch_size]
                if batch:
                    result = test_passwords_worker((zip_path, batch))
                    if result:
                        stop_flag.value = 1
                        return result

    except Exception as e:
        print(f"Error in process {process_id}: {str(e)}")
        return None

    return None

def generate_password_from_index(charset, length, index):
    password = ""
    base = len(charset)
    for _ in range(length):
        password = charset[index % base] + password
        index //= base
    return password


class Cracker:
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.settings = self.progress_manager.settings
        self.smallest_file = None
        self.pause_flag = Value('i', 0)
        self.current_min_index = Value('i', 2 ** 31 - 1)
        self.chunk_size = 5 * 1024 * 1024

    def cracker(self, zf, password):
        try:
            zf.setpassword(password.encode('utf-8'))
            if self.smallest_file:
                zf.extract(self.smallest_file)
                return password
        except (RuntimeError, pyzipper.BadZipFile, Exception):
            return None

    def bf_for_each_process(self, id_process, total_combinations, stop_flag, start_index, start_time, zip_path):
        charset = self.settings["charset"]
        p = psutil.Process()
        p.cpu_affinity([id_process % psutil.cpu_count()])

        with pyzipper.AESZipFile(zip_path, 'r') as zf:
            for i in range(id_process + start_index, total_combinations, self.settings["number_workers"]):
                if stop_flag.value:
                    return
                if self.pause_flag.value:
                    with self.current_min_index.get_lock():
                        self.current_min_index.value = min(self.current_min_index.value, i)
                    while self.pause_flag.value:
                        time.sleep(0.1)
                password = generate_password_from_index(charset, self.settings["current_length"], i)
                result = self.cracker(zf, password)
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

        try:
            file_size = os.path.getsize(self.settings["wordlist_path"])

            chunk_size = file_size // self.settings["number_workers"]

            chunks = []
            for i in range(self.settings["number_workers"]):
                start = i * chunk_size
                size = chunk_size if i < self.settings["number_workers"] - 1 else file_size - start
                chunks.append((start, size))

                # Tạo và khởi chạy các process
                processes = []
                for i in range(self.settings["number_workers"]):
                    p = Process(
                        target=process_chunk_worker,
                        args=(
                            chunks[i][0],  # chunk_start
                            chunks[i][1],  # chunk_size
                            self.settings["wordlist_path"],
                            self.settings["zip_path"],
                            i,  # process_id cho CPU affinity
                            stop_flag
                        )
                    )
                    processes.append(p)
                    p.start()

                # Đợi kết quả từ các process
                result = None
                for p in processes:
                    p.join()
                    if stop_flag.value:
                        # Nếu tìm thấy mật khẩu, dừng các process còn lại
                        for other_p in processes:
                            if other_p != p and other_p.is_alive():
                                other_p.terminate()

            if stop_flag.value:
                messagebox.showinfo(
                    "Success",
                    f"Password: {result}, cracking time: {time.time() - start_time:.2f} seconds")

            else:
                messagebox.showinfo(
                    "Unsuccessful",
                    f"Password not found, cracking time: {time.time() - start_time:.2f} seconds")


        except Exception as e:
            messagebox.showerror("Error", f"Dictionary attack error: {str(e)}")

        finally:
            self.progress_manager.delete_progress()
