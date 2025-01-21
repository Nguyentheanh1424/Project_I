import os
import queue
import time
from dataclasses import dataclass
from multiprocessing import Process, Manager, Value, Queue
from tkinter import messagebox
from typing import Tuple, Optional, Dict, Any

import psutil
import pyzipper

from progress_manager import ProgressManager


@dataclass
class CrackerSettings:
    zip_path: str
    mode: str
    number_workers: int
    current_index: int = 0
    charset: str = ""
    max_length: int = 0
    current_length: int = 1
    wordlist_path: str = ""
    passwords_tried: int = 0


class Cracker:
    BATCH_SIZE = 1000
    QUEUE_MAX_SIZE = 30000

    def __init__(self):
        self.progress_manager = ProgressManager()
        self.settings: Dict[str, Any] = self.progress_manager.settings
        self.smallest_file: Optional[str] = None

        self.pause_flag = Value('i', 0)
        self.stop_flag = Value('i', 0)
        self.current_min_index = Value('i', 2 ** 31 - 1)
        self.total_password = Value('i', 0)
        self.passwords_tried = Value('i', 0)

        self.index_queue: Optional[Queue] = None
        self.start_time: Optional[float] = None

    def validate_settings(self) -> None:
        try:
            if not self.settings.get("zip_path") or not os.path.exists(self.settings["zip_path"]):
                raise ValueError("Invalid ZIP file path.")

            if self.settings["mode"] == "Brute Force":
                if not self.settings.get("charset"):
                    raise ValueError("Character set required for brute force attack")
                if not self.settings.get("max_length", 0) > 0:
                    raise ValueError("Maximum length must be greater than 0")
            elif self.settings["mode"] == "Dictionary Attack":
                if not self.settings.get("wordlist_path") or not os.path.exists(self.settings["wordlist_path"]):
                    raise ValueError("Valid wordlist file path required")

        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            raise

    @staticmethod
    def find_smallest_file(zip_path: str) -> Tuple[Optional[str], bool]:
        try:
            with pyzipper.AESZipFile(zip_path, 'r') as zf:
                files = [(f.filename, f.file_size) for f in zf.infolist() if not f.is_dir()]
                if not files:
                    return None, False
                smallest_file = min(files, key=lambda x: x[1])[0]
                return smallest_file, True
        except Exception as e:
            raise ValueError(f"Error accessing ZIP file: {e}")

    @staticmethod
    def try_password(zf: pyzipper.AESZipFile, password: bytes,
                     smallest_file: str) -> bool:
        try:
            zf.setpassword(password)
            if zf.testzip() is None:
                zf.extract(smallest_file)
                return True
            return False
        except (pyzipper.BadZipFile, RuntimeError):
            return False
        except Exception as e:
            print(f"Unexpected error testing password: {e}")
            return False

    def brute_force(self, settings: Dict[str, Any]) -> None:
        try:
            self.settings = settings
            self.validate_settings()
            self.start_time = time.time()

            charset = self.settings["charset"]
            self.stop_flag.value = 0

            if "passwords_tried" in self.settings:
                self.passwords_tried.value = self.settings["passwords_tried"]

            self.smallest_file, has_file = self.find_smallest_file(self.settings["zip_path"])
            if not has_file:
                messagebox.showerror("Error", "ZIP file contains no files")
                return

            total = sum(len(charset) ** length
                        for length in range(self.settings["current_length"],
                                            self.settings["max_length"] + 1))
            self.total_password.value = total

            with Manager() as manager:
                found_password = manager.Value('s', '')
                self._execute_brute_force_attack(charset, found_password, manager)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _execute_brute_force_attack(self, charset: str, found_password: Value,
                                    manager: Manager) -> None:
        for password_length in range(self.settings["current_length"],
                                     self.settings["max_length"] + 1):
            if self.stop_flag.value:
                break

            self.settings["current_length"] = password_length
            total_combinations = len(charset) ** password_length

            self.index_queue = manager.Queue(maxsize=self.QUEUE_MAX_SIZE)

            if not self._run_attack_processes(total_combinations, found_password):
                return

            self.settings["current_index"] = 0

        self._show_results(found_password.value)

    def _producer_process(self, total_combinations: int, pause_flag: Value) -> None:
        try:
            process = psutil.Process()
            process.cpu_affinity([self.settings["number_workers"]-1])

            current_index = self.settings["current_index"]

            while current_index < total_combinations and not self.stop_flag.value:
                if pause_flag.value:
                    time.sleep(0.1)
                    continue

                batch_end = min(current_index + self.BATCH_SIZE, total_combinations)
                batch = list(range(current_index, batch_end))

                try:
                    self.index_queue.put(batch)
                except queue.Full:
                    time.sleep(0.1)
                    continue

                current_index = batch_end

            for _ in range(self.settings["number_workers"]):
                self.index_queue.put(None)

        except Exception as e:
            print(f"Error in producer process: {e}")
            for _ in range(self.settings["number_workers"]):
                try:
                    self.index_queue.put(None)
                except:
                    pass

    def _worker_process(self, worker_id: int, current_min_index: Value,
                        zip_path: str, pause_flag: Value, found_password: Value) -> None:
        try:
            process = psutil.Process()
            process.cpu_affinity([worker_id % self.settings["number_workers"]])

            charset = self.settings["charset"]
            encoded_chars = [c.encode('utf-8') for c in charset]

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
                                    current_min_index.value = min(
                                        current_min_index.value,
                                        index
                                    )
                                while pause_flag.value and not self.stop_flag.value:
                                    time.sleep(0.1)
                                continue

                            password_chars = [''] * self.settings["current_length"]
                            current_index = index
                            base = len(charset)

                            for i in range(self.settings["current_length"] - 1, -1, -1):
                                password_chars[i] = encoded_chars[current_index % base]
                                current_index //= base

                            password = b''.join(password_chars)

                            try:
                                zf.setpassword(password)
                                if zf.testzip() is None:
                                    zf.extract(self.smallest_file)
                                    self.stop_flag.value = 1
                                    found_password.value = password
                                    return
                            except (pyzipper.BadZipFile, RuntimeError):
                                continue

                        with self.passwords_tried.get_lock():
                            self.passwords_tried.value += len(batch)

                    except queue.Empty:
                        continue

        except Exception as e:
            print(f"Error in worker {worker_id}: {e}")

    def _run_attack_processes(self, total_combinations: int,
                              found_password: Value) -> bool:
        try:
            producer = Process(
                target=self._producer_process,
                args=(total_combinations, self.pause_flag)
            )
            producer.daemon = True
            producer.start()

            workers = []
            for worker_id in range(self.settings["number_workers"]):
                worker = Process(
                    target=self._worker_process,
                    args=(
                        worker_id,
                        self.current_min_index,
                        self.settings["zip_path"],
                        self.pause_flag,
                        found_password
                    )
                )
                worker.daemon = True
                workers.append(worker)
                worker.start()

            producer.join()
            for worker in workers:
                worker.join()

            if self.pause_flag.value:
                self.progress_manager.save_progress(
                    self.current_min_index.value,
                    self.passwords_tried.value
                )
                return False

            return True

        except Exception as e:
            print(f"Error in attack processes: {e}")
            return False

    def dictionary_attack(self, settings: Dict[str, Any]) -> None:
        try:
            self.settings = settings
            self.validate_settings()
            self.start_time = time.time()
            self.stop_flag.value = 0

            if "passwords_tried" in self.settings:
                self.passwords_tried.value = self.settings["passwords_tried"]

            self.smallest_file, has_file = self.find_smallest_file(self.settings["zip_path"])
            if not has_file:
                messagebox.showerror("Error", "ZIP file contains no files")
                return

            available_memory = psutil.virtual_memory().available
            max_batch_memory = self.BATCH_SIZE * 100
            self.QUEUE_MAX_SIZE = min(
                30000,
                max(1000, available_memory // (max_batch_memory * 2))
            )

            with open(self.settings["wordlist_path"], 'rb') as f:
                self.total_password.value = sum(1 for _ in f)

            with Manager() as manager:
                password_queue = manager.Queue(maxsize=self.QUEUE_MAX_SIZE)
                found_password = manager.Value('s', '')

                self._execute_dictionary_attack(password_queue, found_password)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _execute_dictionary_attack(self, password_queue: Queue,
                                   found_password: Value):
        try:
            producer = Process(
                target=self._dict_producer_process,
                args=(password_queue,)
            )
            producer.daemon = True
            producer.start()

            consumers = []
            for process_id in range(self.settings["number_workers"]):
                consumer = Process(
                    target=self._dict_consumer_process,
                    args=(
                        process_id,
                        password_queue,
                        found_password
                    )
                )
                consumer.daemon = True
                consumers.append(consumer)
                consumer.start()

            producer.join()
            for consumer in consumers:
                consumer.join()

            self._show_results(found_password.value)

        except Exception as e:
            print(f"Error in dictionary attack: {e}")

    def _dict_producer_process(self, password_queue: Queue) -> None:
        try:
            batch = []
            batch_size = 0
            last_position = 0

            optimal_batch_size = max(50, min(self.BATCH_SIZE,
                                              self.QUEUE_MAX_SIZE // (self.settings["number_workers"] * 2)))

            with open(self.settings["wordlist_path"], 'rb', buffering=8192 * 1024) as f:
                if self.passwords_tried.value > 0:
                    for _ in range(self.passwords_tried.value):
                        f.readline()
                    last_position = f.tell()

                while not self.stop_flag.value:
                    if self.pause_flag.value:
                        last_position = f.tell()
                        time.sleep(0.01)
                        continue

                    try:
                        chunk = f.read(optimal_batch_size * 100)
                        if not chunk:
                            break

                        lines = chunk.splitlines()
                        if not f.tell() >= os.path.getsize(self.settings["wordlist_path"]):
                            f.seek(f.tell() - len(lines[-1]))
                            lines = lines[:-1]

                        for password in lines:
                            if password.strip():
                                batch.append(password.strip())
                                batch_size += 1

                                if batch_size >= optimal_batch_size:
                                    while not self.stop_flag.value:
                                        try:
                                            password_queue.put((batch, batch_size, last_position), timeout=0.1)
                                            batch = []
                                            batch_size = 0
                                            last_position = f.tell()
                                            break
                                        except queue.Full:
                                            time.sleep(0.01)

                    except Exception as e:
                        print(f"Error reading chunk: {e}")
                        continue

                if batch:
                    while not self.stop_flag.value:
                        try:
                            password_queue.put((batch, batch_size, last_position), timeout=0.1)
                            break
                        except queue.Full:
                            time.sleep(0.01)

        except Exception as e:
            print(f"Error in producer: {e}")
        finally:
            for _ in range(self.settings["number_workers"]):
                try:
                    password_queue.put(None)
                except:
                    pass

    def _dict_consumer_process(self, process_id: int, password_queue: Queue,
                               found_password: Value) -> None:
        try:
            with pyzipper.AESZipFile(self.settings["zip_path"], 'r') as zf:
                while not self.stop_flag.value:
                    try:
                        batch_data = password_queue.get(timeout=0.5)
                        if batch_data is None:
                            break

                        passwords, batch_size, last_position = batch_data

                        for password in passwords:
                            if self.stop_flag.value:
                                return

                            if self.pause_flag.value:
                                self.progress_manager.save_progress(last_position,
                                                                    self.passwords_tried.value)
                                while self.pause_flag.value and not self.stop_flag.value:
                                    time.sleep(0.01)
                                continue

                            try:
                                zf.setpassword(password)
                                if zf.testzip() is None:
                                    self.stop_flag.value = 1
                                    found_password.value = password.decode('utf-8', errors='ignore')
                                    return
                            except (pyzipper.BadZipFile, RuntimeError):
                                continue
                            except Exception:
                                pass

                        with self.passwords_tried.get_lock():
                            self.passwords_tried.value += batch_size

                    except queue.Empty:
                        continue

        except Exception as e:
            print(f"Error in consumer {process_id}: {e}")

    def _show_results(self, password: str) -> None:
        elapsed_time = time.time() - self.start_time

        if password:
            self.passwords_tried.value = self.total_password.value
            messagebox.showinfo(
                "Success",
                f"Password found: {password}\n"
                f"Time taken: {elapsed_time:.2f} seconds"
            )
        else:
            messagebox.showinfo(
                "Unsuccessful",
                f"Password not found\n"
                f"Time taken: {elapsed_time:.2f} seconds"
            )

        self.progress_manager.delete_progress()