import logging
import multiprocessing
import pyzipper
import os

class PasswordCracker:
    def __init__(self, zip_file, char_set, max_length):
        self.zip_file = zip_file
        self.char_set = char_set
        self.max_length = max_length
        self.stop_flag = multiprocessing.Manager().Event()

    def validate_zip_file(self):
        """Kiểm tra tệp ZIP."""
        if not os.path.isfile(self.zip_file):
            logging.error(f"Tệp ZIP không tồn tại: {self.zip_file}")
            return False
        try:
            with pyzipper.AESZipFile(self.zip_file, 'r') as zf:
                zf.testzip()
            return True
        except pyzipper.BadZipFile:
            logging.error("Tệp ZIP không hợp lệ.")
            return False

    def generate_password_chunk(self, length, start, chunk_size):
        """Tạo mật khẩu cho chunk."""
        base = len(self.char_set)
        chunk = []
        total_combinations = base ** length
        for i in range(start, min(start + chunk_size, total_combinations)):
            password = ""
            idx = i
            for _ in range(length):
                password = self.char_set[idx % base] + password
                idx //= base
            chunk.append(password)
        return chunk

    def crack_password(self, password):
        """Thử giải mã mật khẩu."""
        if self.stop_flag.is_set():
            return None
        try:
            with pyzipper.AESZipFile(self.zip_file, 'r') as zf:
                zf.extractall(pwd=password.encode('utf-8'))
            return password
        except (RuntimeError, pyzipper.BadZipFile):
            return None
