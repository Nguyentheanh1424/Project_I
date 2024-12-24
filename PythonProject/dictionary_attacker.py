import concurrent
import itertools
import multiprocessing
from asyncio import Queue

import pyzipper


class DictionaryAttacker:
    def __init__(self, zip_file, progress_manager):
        self.zip_file = zip_file
        self.progress_manager = progress_manager
        self.stop_flag = multiprocessing.Manager().Event()
        self.progress_queue = Queue()
        self.executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=min(multiprocessing.cpu_count(), 4)
        )

    def try_password(self, password, result_queue):
        if self.stop_flag.is_set():
            return
        try:
            with pyzipper.AESZipFile(self.zip_file, 'r') as zf:
                zf.extractall(pwd=password.encode('utf-8'))
            self.stop_flag.set()
            result_queue.put(password)
        except (RuntimeError, pyzipper.BadZipFile):
            return

    def attack(self, wordlist_file, progress_var, status_label):
        result_queue = multiprocessing.Manager().Queue()
        total_words = sum(1 for _ in open(wordlist_file, 'r', encoding='utf-8', errors='ignore'))
        processed_words = 0

        with open(wordlist_file, 'r', encoding='utf-8', errors='ignore') as f:
            while True:
                # Đọc và xử lý theo batch để tối ưu bộ nhớ
                passwords = [line.strip() for line in itertools.islice(f, 1000)]
                if not passwords:
                    break

                futures = [
                    self.executor.submit(self.try_password, password, result_queue)
                    for password in passwords
                ]

                for _ in concurrent.futures.as_completed(futures):
                    if not result_queue.empty():
                        password = result_queue.get()
                        status_label.config(
                            text=f"Đã tìm thấy mật khẩu: {password}")
                        self.executor.shutdown()
                        return password

                processed_words += len(passwords)
                progress = (processed_words / total_words) * 100
                progress_var.set(progress)
                status_label.config(
                    text=f"Đã thử {processed_words}/{total_words} từ...")

        status_label.config(text="Không tìm thấy mật khẩu trong từ điển")
        self.executor.shutdown()
        return None