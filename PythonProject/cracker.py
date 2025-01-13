import os
import queue
import time
from multiprocessing import Process, Manager, Value, Queue
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
        self.stop_flag = Value('i', 0)
        self.current_min_index = Value('i', 2 ** 31 - 1)
        self.total_password = Value('i', 0)
        self.passwords_tried = Value('i', 0)
        self.index_queue = None
        self.batch_size = 2500
        self.start_time = None

    def turn_stop_flag(self, flag):
        self.stop_flag = flag

    def validate_settings(self):
        try:
            if not self.settings.get("zip_path") or not os.path.exists(self.settings["zip_path"]):
                raise ValueError("Invalid ZIP file path.")
            if not 1 <= self.settings.get("number_workers") <= os.cpu_count() - 2:
                raise ValueError("Invalid number of CPU cores.")
            if self.settings["mode"] == "Brute Force":
                if not self.settings.get("charset"):
                    raise ValueError("Character set (charset) is required for brute force.")
                if not self.settings.get("max_length") > 0:
                    raise ValueError("Maximum length for brute force must be greater than 0.")
            elif self.settings["mode"] == "Dictionary Attack":
                if not self.settings.get("wordlist_path") or not os.path.exists(self.settings["wordlist_path"]):
                    raise ValueError("Valid wordlist file path is required for dictionary attack.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    @staticmethod
    def find_smallest_file(zip_path):
        with pyzipper.AESZipFile(zip_path, 'r') as zf:
            min_size = float('inf')
            smallest_file = None
            has_file = False

            for file_info in zf.infolist():
                if file_info.is_dir():
                    continue
                has_file = True
                if file_info.file_size < min_size:
                    min_size = file_info.file_size
                    smallest_file = file_info.filename

        return smallest_file, has_file

    def cracker(self, zf, charset, length, index, encoded_chars):
        try:
            password_chars = [''] * length
            base = len(charset)

            for i in range(length - 1, -1, -1):
                password_chars[i] = encoded_chars[index % base]
                index //= base

            password = b''.join(password_chars)

            zf.setpassword(password)
            if zf.testzip() is None:
                zf.extract(self.smallest_file)
                return password.decode('utf-8')
        except (pyzipper.BadZipFile, RuntimeError, Exception):
            return None

    def index_producer(self, total_combinations, pause_flag):
        try:
            p = psutil.Process()
            p.cpu_affinity([self.settings["number_workers"]])

            current_index = self.settings["current_index"]
            while current_index < total_combinations and not self.stop_flag.value:
                if pause_flag.value:
                    time.sleep(0.1)
                    continue

                batch_end = min(current_index + self.batch_size, total_combinations)
                batch = list(range(current_index, batch_end))
                self.index_queue.put(batch)
                current_index = batch_end

            for _ in range(self.settings["number_workers"]):
                self.index_queue.put(None)

        except Exception as e:
            print(f"Error in producer: {e}")
            for _ in range(self.settings["number_workers"]):
                self.index_queue.put(None)

    def bf_worker(self, id_process, current_min_index, start_time, zip_path, pause_flag):
        try:
            charset = self.settings["charset"]
            encoded_chars = [c.encode('utf-8') for c in charset]

            p = psutil.Process()
            p.cpu_affinity([id_process % self.settings["number_workers"]])

            with pyzipper.AESZipFile(zip_path, 'r') as zf:
                while not self.stop_flag.value:
                    try:
                        batch = self.index_queue.get(timeout=1)
                        if batch is None:
                            break

                        for index in batch:
                            if self.stop_flag.value:
                                break

                            if pause_flag.value:
                                with current_min_index.get_lock():
                                    current_min_index.value = min(current_min_index.value, index)
                                while pause_flag.value and not self.stop_flag.value:
                                    time.sleep(0.1)
                                continue

                            result = self.cracker(zf, charset, self.settings["current_length"],
                                                index, encoded_chars)
                            if result:
                                self.passwords_tried.value = self.total_password.value
                                self.stop_flag.value = 1
                                messagebox.showinfo(
                                    "Success",
                                    f"Password: {result}, cracking time: {time.time() - start_time:.2f} seconds")
                                self.progress_manager.delete_progress()
                                return

                        with self.passwords_tried.get_lock():
                            self.passwords_tried.value += len(batch)

                    except queue.Empty:
                        continue

        except Exception as e:
            print(f"Error in worker {id_process}: {e}")

    def brute_force(self, settings):
        self.settings = settings
        self.validate_settings()
        self.start_time = time.time()
        charset = self.settings["charset"]

        with self.stop_flag.get_lock():
            self.stop_flag.value = 0

        if "passwords_tried" in self.settings:
            with self.passwords_tried.get_lock():
                self.passwords_tried.value = self.settings["passwords_tried"]

        self.smallest_file, has_file = self.find_smallest_file(self.settings["zip_path"])
        if not has_file:
            messagebox.showerror("Error", "ZIP file contains no files, only directories")
            return

        total = 0
        for length in range(self.settings["current_length"], self.settings["max_length"] + 1):
            total += len(charset) ** length
        with self.total_password.get_lock():
            self.total_password.value = total

        with Manager() as manager:
            for password_length in range(self.settings["current_length"], self.settings["max_length"] + 1):
                self.settings["current_length"] = password_length
                total_combinations = len(charset) ** password_length

                self.index_queue = manager.Queue(maxsize=30000)

                producer = Process(
                    target=self.index_producer,
                    args=(total_combinations, self.pause_flag)
                )
                producer.daemon = True
                producer.start()

                workers = []
                for id_process in range(self.settings["number_workers"]):
                    worker = Process(
                        target=self.bf_worker,
                        args=(
                            id_process,
                            self.current_min_index,
                            self.start_time,
                            self.settings["zip_path"],
                            self.pause_flag
                        )
                    )
                    worker.daemon = True
                    workers.append(worker)
                    worker.start()

                producer.join()
                for worker in workers:
                    worker.join()

                self.settings["current_index"] = 0

                if self.pause_flag.value:
                    self.progress_manager.save_progress(self.current_min_index.value, self.passwords_tried.value)
                    return
        if self.stop_flag.value == 0:
            messagebox.showinfo(
                "Unsuccessful",
                f"Password not found, cracking time: {time.time() - self.start_time:.2f} seconds")
        self.progress_manager.delete_progress()

    def dictionary_attack(self, settings):
        self.settings = settings
        self.validate_settings()
        self.start_time = time.time()

        with self.stop_flag.get_lock():
            self.stop_flag.value = 0

        wordlist_path = self.settings["wordlist_path"]
        zip_path = self.settings["zip_path"]
        number_workers = self.settings["number_workers"]

        if "passwords_tried" in self.settings:
            with self.passwords_tried.get_lock():
                self.passwords_tried.value = self.settings["passwords_tried"]

        with open(wordlist_path, 'rb') as f:
            self.total_password.value = sum(chunk.count(b'\n') for chunk in iter(lambda: f.read(8192), b''))

        self.smallest_file, has_file = self.find_smallest_file(zip_path)
        if not has_file:
            print("Error: ZIP file contains no files, only directories.")
            return

        try:
            with Manager() as manager:
                password_queue = manager.Queue(maxsize=30000)
                found_password = manager.Value('s', '')
                processes = []

                producer = Process(
                    target=self.password_producer,
                    args=(wordlist_path, password_queue, self.stop_flag, number_workers)
                )
                producer.daemon = True
                producer.start()

                for process_id in range(number_workers):
                    consumer = Process(
                        target=self.password_consumer,
                        args=(
                            zip_path,
                            password_queue,
                            self.stop_flag,
                            found_password,
                            self.smallest_file,
                            process_id,
                            number_workers,
                            self.passwords_tried,
                            self.pause_flag
                        )
                    )
                    consumer.daemon = True
                    processes.append(consumer)
                    consumer.start()

                producer.join()
                for process in processes:
                    process.join()

                if self.stop_flag.value:
                    self.passwords_tried.value = self.total_password.value
                    messagebox.showinfo(
                        "Success",
                        f"Password: {found_password.value}, cracking time: {time.time() - self.start_time:.2f} seconds")
                    self.progress_manager.delete_progress()
                else:
                    messagebox.showinfo(
                        "Unsuccessful",
                        f"Password not found, cracking time: {time.time() - self.start_time:.2f} seconds")
                    self.progress_manager.delete_progress()

        except Exception as e:
            print(f"Error: {e}")


    def password_producer(self, wordlist_path: str, password_queue: Queue,
                          stop_flag: Value, num_consumers: int):
        p = psutil.Process()
        p.cpu_affinity([num_consumers])

        try:
            batch = []
            batch_size_lines = 0

            with open(wordlist_path, 'r', encoding='utf-8') as file:
                # Skip lines until start_line
                for _ in range(self.passwords_tried.value):
                    next(file)

            with open(wordlist_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if stop_flag.value:
                        break

                    password = line.strip()
                    if not password:
                        continue

                    batch.append(password)
                    batch_size_lines += 1

                    if batch_size_lines >= self.batch_size:
                        password_queue.put((batch, batch_size_lines))
                        batch = []
                        batch_size_lines = 0

                if batch:
                    password_queue.put((batch, batch_size_lines))

                for _ in range(num_consumers):
                    password_queue.put(None)

        except Exception as e:
            print(f"Error in producer: {e}")
        finally:
            for _ in range(num_consumers):
                password_queue.put(None)

    @staticmethod
    def password_consumer(zip_path: str, password_queue: Queue, stop_flag: Value,
                          found_password: Value, smallest_file: str,
                          process_id: int, num_workers: int,
                          passwords_tried: Value, pause_flag: Value):
        try:
            p = psutil.Process()
            p.cpu_affinity([process_id % num_workers])

            with pyzipper.AESZipFile(zip_path, 'r') as zf:
                while True:
                    try:
                        batch_data = password_queue.get(timeout=1)
                    except queue.Empty:
                        continue

                    if batch_data is None:
                        return

                    batch, batch_size_lines = batch_data

                    for password in batch:
                        if stop_flag.value:
                            return

                        while pause_flag.value and not stop_flag.value:
                            time.sleep(0.1)

                        try:
                            encoded_password = password.encode('utf-8')
                            zf.setpassword(encoded_password)

                            if zf.testzip() is None:
                                zf.extract(smallest_file)
                                stop_flag.value = 1
                                found_password.value = password
                                return

                        except (RuntimeError, pyzipper.BadZipFile, Exception):
                            continue
                    with passwords_tried.get_lock():
                        passwords_tried.value += batch_size_lines

        except Exception as e:
            messagebox.showerror("Error", f"Error in consumer {process_id}: {e}")
