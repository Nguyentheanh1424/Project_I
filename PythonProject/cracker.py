import concurrent.futures
import multiprocessing
import pyzipper
import time
from queue import Queue, Empty
import threading
from password_generator import PasswordGenerator


def _crack_worker(zip_file, password, stop_flag, result_queue):
    if stop_flag.is_set():
        return
    try:
        with pyzipper.AESZipFile(zip_file, 'r') as zf:
            zf.extractall(pwd=password.encode('utf-8'))
        stop_flag.set()
        result_queue.put(password)
    except (RuntimeError, pyzipper.BadZipFile):
        return


class CrackerBase:
    def __init__(self, settings, progress_manager):
        self.settings = settings
        self.progress_manager = progress_manager
        self.stop_flag = multiprocessing.Manager().Event()
        self.progress_queue = Queue()
        self.executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=self.settings["process_var"]
        )

    def run_cracking(self, zip_file, passwords):
        """Chạy cracking với một danh sách mật khẩu."""
        result_queue = multiprocessing.Manager().Queue()
        futures = [
            self.executor.submit(_crack_worker, zip_file, password,
                                 self.stop_flag, result_queue)
            for password in passwords
        ]
        for _ in concurrent.futures.as_completed(futures):
            if not result_queue.empty():
                return result_queue.get()
        return None

    def _handle_success(self, result, start_time, status_label, progress_var):
        elapsed_time = time.time() - start_time
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        status_label.config(
            text=f"Mật khẩu đã giải mã thành công: {result}\n"
                 f"Thời gian: {formatted_time}"
        )
        self.progress_manager.delete_progress()
        progress_var.set(100)

    def _handle_failure(self, start_time, status_label, progress_var):
        elapsed_time = time.time() - start_time
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        status_label.config(
            text=f"Không tìm thấy mật khẩu.\nThời gian: {formatted_time}")
        progress_var.set(0)
        self.progress_manager.delete_progress()


class BruteForce(CrackerBase):
    def __init__(self, settings, progress_manager):
        super().__init__(settings, progress_manager)
        self.password_generator = PasswordGenerator()

    def start_cracking(self, progress_var, validate_progress, status_label):
        if validate_progress:
            progress = self.progress_manager.load_progress()
        else:
            progress = {"current_length": 1, "current_index": 0}

        start_time = time.time()

        def update_progress():
            while True:
                try:
                    new_progress = self.progress_queue.get(timeout=1)
                    progress_var.set(new_progress)
                except Empty:
                    if self.stop_flag.is_set():
                        break

        threading.Thread(target=update_progress, daemon=True).start()

        chars_set = list(self.settings["character_set"])

        for length in range(progress["current_length"], self.settings["max_password_length"] + 1):
            total_combinations = len(self.settings["character_set"]) ** length
            status_label.config(text=f"Đang thử mật khẩu độ dài {length}...")

            chunk_size = max(total_combinations // self.settings["process_var"], 1000)

            for start in range(progress["current_index"], total_combinations, chunk_size):
                passwords = list(
                    self.password_generator.generate_password_chunk_numpy(
                        chars_set, length, start, chunk_size, total_combinations
                    )
                )

                result = self.run_cracking(
                    self.settings["zip_file"], passwords
                )

                if result:
                    self._handle_success(result, start_time, status_label, progress_var)
                    return

                self.progress_manager.save_progress(progress, self.settings, length, start + chunk_size)
                self.progress_queue.put((start + chunk_size) / total_combinations * 100)

            progress["current_index"] = 0
            progress["current_length"] += 1
            progress_var.set(0)

        self._handle_failure(start_time, status_label, progress_var)
        self.progress_queue.put(0)


class DictionaryAttacker(CrackerBase):
    def __init__(self, settings, progress_manager):
        super().__init__(settings, progress_manager)

    def start_cracking(self, wordlist_path, progress_var, status_label):
        start_time = time.time()

        def update_progress():
            while True:
                try:
                    new_progress = self.progress_queue.get(timeout=1)
                    progress_var.set(new_progress)
                except Empty:
                    if self.stop_flag.is_set():
                        break

        threading.Thread(target=update_progress, daemon=True).start()

        try:
            with open(wordlist_path, "r", encoding="utf-8") as f:
                passwords = f.readlines()

            total_passwords = len(passwords)
            chunk_size = max(total_passwords // self.settings["process_var"], 1000)

            for start in range(0, total_passwords, chunk_size):
                chunk = passwords[start:start + chunk_size]
                chunk = [pwd.strip() for pwd in chunk]

                result = self.run_cracking(
                    self.settings["zip_file"], chunk
                )

                if result:
                    self._handle_success(result, start_time, status_label, progress_var)
                    return

                self.progress_queue.put((start + chunk_size) / total_passwords * 100)

        except Exception as e:
            status_label.config(text=f"Lỗi khi đọc wordlist: {e}")

        self._handle_failure(start_time, status_label, progress_var)
        self.progress_queue.put(0)
