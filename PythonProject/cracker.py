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

    def _update_progress(self, progress_var):
        """Cập nhật thanh tiến trình."""
        while True:
            try:
                new_progress = self.progress_queue.get(timeout=1)
                progress_var.set(new_progress)
            except Empty:
                if self.stop_flag.is_set():
                    break

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

        threading.Thread(target=self._update_progress, args=(progress_var,), daemon=True).start()

        progress_var.set(0)

        chars_set = list(self.settings["character_set"])

        status_label.config(text=f"Đang thử mật khẩu...")

        total_combinations = len(chars_set) ** self.settings["max_password_length"]

        current_combinations = 0

        if total_combinations <= 1000: chunk_size = total_combinations
        else:
            chunk_size = (total_combinations // self.settings["process_var"]) // 10
            if chunk_size >= 10000: chunk_size = 10000

        for length in range(progress["current_length"], self.settings["max_password_length"] + 1):
            combinations = len(chars_set) ** length

            for start in range(progress["current_index"], combinations, chunk_size):
                end = min(start + chunk_size, combinations)
                current_chunk_size = end - start
                passwords = list(
                    self.password_generator.generate_password_chunk_numpy(
                        chars_set, length, start, end
                    )
                )

                result = self.run_cracking(
                    self.settings["zip_file"], passwords
                )

                if result:
                    self._handle_success(result, start_time, status_label, progress_var)
                    return

                self.progress_manager.save_progress(
                    "Brute Force",
                    self.settings,
                    current_length=length,
                    current_index=start + chunk_size
                )
                current_combinations += current_chunk_size
                self.progress_queue.put(current_combinations / total_combinations * 100)

            progress["current_index"] = 0
            progress["current_length"] += 1

        self._handle_failure(start_time, status_label, progress_var)
        self.progress_queue.put(0)


class DictionaryAttacker(CrackerBase):
    def __init__(self, settings, progress_manager):
        super().__init__(settings, progress_manager)

    def start_cracking(self, wordlist_path, progress_var, status_label):
        start_time = time.time()
        status_label.config(text=f"Đang thử mật khẩu...")

        # Bắt đầu luồng cập nhật tiến trình
        threading.Thread(target=self._update_progress, args=(progress_var,), daemon=True).start()

        progress_var.set(0)

        try:
            with open(wordlist_path, "r", encoding="utf-8") as f:
                total_passwords = sum(1 for _ in f)  # Tổng số mật khẩu trong wordlist
                f.seek(0)

                # Khôi phục tiến trình nếu có
                saved_progress = self.progress_manager.load_progress()
                if saved_progress:
                    current_index = saved_progress.get("current_index", 0)
                    f.seek(current_index)  # Đọc tiếp từ vị trí lưu trước
                else:
                    current_index = 0

                chunk_size = max(total_passwords // self.settings["process_var"] // 10, 1000)

                for chunk in self._read_wordlist_in_chunks(f, chunk_size):
                    result = self.run_cracking(self.settings["zip_file"], chunk)

                    if result:
                        self._handle_success(result, start_time, status_label, progress_var)
                        return

                    # Cập nhật vị trí hiện tại
                    current_index += sum(len(line) + 1 for line in chunk)  # Cộng số byte của mỗi dòng

                    # Lưu tiến trình
                    self.progress_manager.save_progress(
                        mode="Dictionary Attack",
                        settings=self.settings,
                        current_index=current_index,
                        wordlist_path=wordlist_path
                    )

                    # Cập nhật thanh tiến trình
                    progress_var.set(min(progress_var.get() + len(chunk) / total_passwords * 100, 100))

        except FileNotFoundError:
            status_label.config(text="Wordlist không tồn tại.")
        except Exception as e:
            status_label.config(text=f"Lỗi khi đọc wordlist: {e}")

        self._handle_failure(start_time, status_label, progress_var)
        self.progress_queue.put(0)

    @staticmethod
    def _read_wordlist_in_chunks(file_obj, chunk_size):
        """
        Đọc tệp wordlist theo từng chunk để giảm sử dụng bộ nhớ.

        Args:
            file_obj (file object): Tệp wordlist đã được mở để đọc chunk mật khẩu.
            chunk_size (int): Số dòng (mật khẩu) tối đa trong mỗi chunk.

        Yields:
            list: Một chunk các dòng từ wordlist, với số dòng tối đa là `chunk_size`.
        """
        # Khởi tạo một chunk rỗng để lưu các dòng từ wordlist
        chunk = []

        # Đọc từng dòng trong tệp wordlist
        for line in file_obj:
            # Loại bỏ khoảng trắng và thêm dòng vào chunk
            chunk.append(line.strip())

            # Khi chunk đạt đến kích thước tối đa (`chunk_size`)
            if len(chunk) >= chunk_size:
                yield chunk  # Trả về chunk hiện tại
                chunk = []  # Reset chunk để bắt đầu nhóm mới

        # Nếu còn sót lại các dòng chưa được trả về (chunk chưa đầy)
        if chunk:
            yield chunk  # Trả về chunk cuối cùng