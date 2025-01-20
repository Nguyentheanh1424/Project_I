import os
import queue
import time
from dataclasses import dataclass
from multiprocessing import Process, Manager, Value, Queue
from tkinter import messagebox
import psutil
import pyzipper
from typing import List, Tuple, Optional, Dict, Any
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

        # Shared multiprocessing values
        self.pause_flag = Value('i', 0)
        self.stop_flag = Value('i', 0)
        self.current_min_index = Value('i', 2 ** 31 - 1)
        self.total_password = Value('i', 0)
        self.passwords_tried = Value('i', 0)

        self.index_queue: Optional[Queue] = None
        self.start_time: Optional[float] = None

    def validate_settings(self) -> None:
        """Validate cracker settings before starting the attack."""
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
        """Find the smallest file in ZIP for efficient password testing."""
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
        """Test a single password against the ZIP file."""
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
        """Execute brute force attack on ZIP file."""
        try:
            self.settings = settings
            self.validate_settings()
            self.start_time = time.time()

            charset = self.settings["charset"]
            self.stop_flag.value = 0

            if "passwords_tried" in self.settings:
                self.passwords_tried.value = self.settings["passwords_tried"]

            # Initialize ZIP file handling
            self.smallest_file, has_file = self.find_smallest_file(self.settings["zip_path"])
            if not has_file:
                messagebox.showerror("Error", "ZIP file contains no files")
                return

            # Calculate total possible passwords
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
        """Execute the main brute force attack logic."""
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
        """
        Process that produces indices for password generation.

        Args:
            total_combinations: Total number of possible combinations
            pause_flag: Shared flag for pausing the process
        """
        try:
            process = psutil.Process()
            process.cpu_affinity([self.settings["number_workers"]])

            current_index = self.settings["current_index"]

            # Generate batches of indices until all combinations are covered
            while current_index < total_combinations and not self.stop_flag.value:
                if pause_flag.value:
                    time.sleep(0.1)
                    continue

                # Calculate batch size and create batch
                batch_end = min(current_index + self.BATCH_SIZE, total_combinations)
                batch = list(range(current_index, batch_end))

                try:
                    self.index_queue.put(batch)
                except queue.Full:
                    time.sleep(0.1)
                    continue

                current_index = batch_end

            # Signal workers to stop by sending None
            for _ in range(self.settings["number_workers"]):
                self.index_queue.put(None)

        except Exception as e:
            print(f"Error in producer process: {e}")
            # Ensure workers are properly signaled to stop on error
            for _ in range(self.settings["number_workers"]):
                try:
                    self.index_queue.put(None)
                except:
                    pass

    def _worker_process(self, worker_id: int, current_min_index: Value,
                        zip_path: str, pause_flag: Value, found_password: Value) -> None:
        """
        Worker process that tests password combinations.

        Args:
            worker_id: ID of the worker process
            current_min_index: Shared value for tracking minimum index
            zip_path: Path to the ZIP file
            pause_flag: Shared flag for pausing the process
            found_password: Shared value for storing found password
        """
        try:
            process = psutil.Process()
            process.cpu_affinity([worker_id % self.settings["number_workers"]])


            # Pre-encode charset for better performance
            charset = self.settings["charset"]
            encoded_chars = [c.encode('utf-8') for c in charset]

            with pyzipper.AESZipFile(zip_path, 'r') as zf:
                while not self.stop_flag.value:
                    try:
                        # Get batch of indices to process
                        batch = self.index_queue.get(timeout=1)
                        if batch is None:
                            break

                        # Process each index in the batch
                        for index in batch:
                            if self.stop_flag.value:
                                break

                            # Handle pause flag
                            if pause_flag.value:
                                with current_min_index.get_lock():
                                    current_min_index.value = min(
                                        current_min_index.value,
                                        index
                                    )
                                while pause_flag.value and not self.stop_flag.value:
                                    time.sleep(0.1)
                                continue

                            # Generate and test password
                            password_chars = [''] * self.settings["current_length"]
                            current_index = index
                            base = len(charset)

                            # Generate password from index
                            for i in range(self.settings["current_length"] - 1, -1, -1):
                                password_chars[i] = encoded_chars[current_index % base]
                                current_index //= base

                            # Join password chars and test
                            password = b''.join(password_chars)

                            try:
                                zf.setpassword(password)
                                if zf.testzip() is None:
                                    # Password found
                                    zf.extract(self.smallest_file)
                                    self.stop_flag.value = 1
                                    found_password.value = password
                                    return
                            except (pyzipper.BadZipFile, RuntimeError):
                                continue

                        # Update progress
                        with self.passwords_tried.get_lock():
                            self.passwords_tried.value += len(batch)

                    except queue.Empty:
                        continue

        except Exception as e:
            print(f"Error in worker {worker_id}: {e}")

    def _run_attack_processes(self, total_combinations: int,
                              found_password: Value) -> bool:
        """Start and manage the producer and worker processes."""
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
        """Execute dictionary attack on ZIP file."""
        try:
            self.settings = settings
            self.validate_settings()
            self.start_time = time.time()
            self.stop_flag.value = 0

            if "passwords_tried" in self.settings:
                self.passwords_tried.value = self.settings["passwords_tried"]

            # Count total passwords in wordlist
            with open(self.settings["wordlist_path"], 'rb') as f:
                self.total_password.value = sum(
                    chunk.count(b'\n')
                    for chunk in iter(lambda: f.read(8192), b'')
                )

            # Validate ZIP file
            self.smallest_file, has_file = self.find_smallest_file(
                self.settings["zip_path"]
            )
            if not has_file:
                raise ValueError("ZIP file contains no files")

            with Manager() as manager:
                password_queue = manager.Queue(maxsize=self.QUEUE_MAX_SIZE)
                found_password = manager.Value('s', '')

                self._execute_dictionary_attack(
                    password_queue,
                    found_password
                )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _execute_dictionary_attack(self, password_queue: Queue,
                                   found_password: Value):
        """Execute the main dictionary attack logic."""
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
        """Process that produces passwords from wordlist."""
        try:
            process = psutil.Process()
            process.cpu_affinity([self.settings["number_workers"]])

            batch: List[str] = []
            batch_size = 0

            with open(self.settings["wordlist_path"], 'r',
                      encoding='utf-8', errors='ignore') as file:
                # Skip previously tried passwords
                for _ in range(self.passwords_tried.value):
                    next(file)

                for line in file:
                    if self.stop_flag.value:
                        break

                    password = line.strip()
                    if password:
                        batch.append(password)
                        batch_size += 1

                        if batch_size >= self.BATCH_SIZE:
                            password_queue.put((batch, batch_size))
                            batch = []
                            batch_size = 0

                if batch:
                    password_queue.put((batch, batch_size))

        except Exception as e:
            print(f"Error in dictionary producer: {e}")
        finally:
            # Signal consumers to stop
            for _ in range(self.settings["number_workers"]):
                password_queue.put(None)

    def _dict_consumer_process(self, process_id: int, password_queue: Queue,
                               found_password: Value) -> None:
        """Process that tests passwords from the queue."""
        try:
            process = psutil.Process()
            process.cpu_affinity([process_id % self.settings["number_workers"]])

            with pyzipper.AESZipFile(self.settings["zip_path"], 'r') as zf:
                while not self.stop_flag.value:
                    try:
                        batch_data = password_queue.get(timeout=1)
                        if batch_data is None:
                            break

                        passwords, batch_size = batch_data
                        for password in passwords:
                            if self.stop_flag.value:
                                return

                            if self.pause_flag.value:
                                while self.pause_flag.value and not self.stop_flag.value:
                                    time.sleep(0.1)
                                continue

                            if self.try_password(zf, password.encode('utf-8'),
                                                 self.smallest_file):
                                self.stop_flag.value = 1
                                found_password.value = password
                                return

                        with self.passwords_tried.get_lock():
                            self.passwords_tried.value += batch_size

                    except queue.Empty:
                        continue

        except Exception as e:
            print(f"Error in dictionary consumer {process_id}: {e}")

    def _show_results(self, password: str) -> None:
        """Display the results of the cracking attempt."""
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