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
    try:
        with pyzipper.AESZipFile(zip_path, 'r') as zf:
            for password in password_batch:
                try:
                    zf.setpassword(password.encode('utf-8'))
                    zf.extractall()
                    return password
                except (RuntimeError, pyzipper.BadZipFile):
                    continue
    except Exception:
        return None
    return None


def process_chunk_worker(args):
    chunk_start, chunk_size, file_path, zip_path = args
    p = psutil.Process()
    worker_id = int(current_process().name.split('-')[-1]) - 1
    p.cpu_affinity([worker_id % psutil.cpu_count()])

    passwords = []

    with open(file_path, 'rb') as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        mm.seek(chunk_start)

        while mm.tell() < chunk_start + chunk_size:
            line = mm.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                break
            passwords.append(line)

            if len(passwords) >= 10000:
                result = test_passwords_worker((zip_path, passwords))
                if result:
                    mm.close()
                    return result
                passwords = []

        if passwords:
            result = test_passwords_worker((zip_path, passwords))
            if result:
                mm.close()
                return result

        mm.close()
    return None

class Cracker:
    def __init__(self):
        self.progress_manager = ProgressManager()
        self.settings = self.progress_manager.settings
        self.smallest_file = None
        self.pause_flag = Value('i', 0)
        self.current_min_index = Value('i', 2 ** 31 - 1)
        self.chunk_size = 1024 * 1024

    def cracker(self, zf, password):
        try:
            zf.setpassword(password.encode('utf-8'))
            if self.smallest_file:
                zf.extract(self.smallest_file)
                return password
        except (RuntimeError, pyzipper.BadZipFile):
            return None
        except Exception:
            return None

    def generate_password_from_index(self, charset, length, index):
        password = ""
        base = len(charset)
        for _ in range(length):
            password = charset[index % base] + password
            index //= base
        return password

    def bf_for_each_process(self, id_process, total_combinations, stop_flag, start_index, start_time, zip_path):
        charset = self.settings["charset"]
        p = psutil.Process()
        p.cpu_affinity([id_process])

        with pyzipper.AESZipFile(zip_path, 'r') as zf:
            for i in range(id_process + start_index, total_combinations, self.settings["number_workers"]):
                if stop_flag.value:
                    return
                if self.pause_flag.value:
                    with self.current_min_index.get_lock():
                        self.current_min_index.value = min(self.current_min_index.value, i)
                    while self.pause_flag.value:
                        time.sleep(0.1)
                password = self.generate_password_from_index(charset, self.settings["current_length"], i)
                result = self.cracker(zf, password)
                if result:
                    stop_flag.value = 1
                    messagebox.showinfo(
                        "Thành công",
                        f"Mật khẩu: {result}, thời gian thám mã: {time.time() - start_time:.2f} giây")
                    self.progress_manager.delete_progress()
                    return

    def brute_force(self):
        start_time = time.time()
        charset = self.settings["charset"]
        stop_flag = Value('i', 0)

        # Tìm tệp nhỏ nhất trong zip trước khi bắt đầu brute force
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

        # Nếu không tìm thấy mật khẩu sau khi thử hết các khả năng
        messagebox.showinfo(
            "Không thành công",
            f"Không tìm thấy mật khẩu, thời gian thám mã: {time.time() - start_time:.2f} giây")
        self.progress_manager.delete_progress()

    def dictionary_attack(self):
        start_time = time.time()

        try:
            file_size = os.path.getsize(self.settings["wordlist_path"])
            num_chunks = max(self.settings["number_workers"] * 2, file_size // self.chunk_size)
            chunk_size = file_size // num_chunks

            chunks = [(i * chunk_size,
                       chunk_size if i < num_chunks - 1 else file_size - i * chunk_size,
                       self.settings["wordlist_path"],
                       self.settings["zip_path"])
                      for i in range(num_chunks)]

            with Pool(processes=self.settings["number_workers"]) as pool:
                result = None
                for res in pool.imap_unordered(process_chunk_worker, chunks):
                    if res:
                        result = res
                        break

            if result:
                messagebox.showinfo(
                    "Thành công",
                    f"Mật khẩu: {result}. Thời gian thám mã: {time.time() - start_time:.2f} giây"
                )
            else:
                messagebox.showinfo(
                    "Không thành công",
                    f"Không tìm thấy mật khẩu. Thời gian: {time.time() - start_time:.2f} giây"
                )

        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi dictionary attack: {str(e)}")

        finally:
            self.progress_manager.delete_progress()
