import os
import logging
import string
import multiprocessing
import json
import pyzipper
from tqdm import tqdm
import sys

# Đặt mã hóa UTF-8 để hỗ trợ tiếng Việt
sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình Logging (chỉ ghi log vào file, không hiển thị log chi tiết)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(processName)s] %(levelname)s: %(message)s',
    handlers=[logging.FileHandler('zip_crack.log', encoding='utf-8')]
)

PROGRESS_FILE = "progress.json"


def _validate_zip_file(zip_file: str) -> bool:
    """Kiểm tra nếu tệp ZIP tồn tại và hợp lệ."""
    if not os.path.isfile(zip_file):
        logging.error(f"Tệp ZIP không tồn tại: {zip_file}")
        return False
    try:
        with pyzipper.AESZipFile(zip_file, 'r'):
            pass
    except pyzipper.BadZipFile:
        logging.error("Tệp ZIP không hợp lệ.")
        return False
    return True


def _save_progress(progress):
    """Lưu tiến độ hiện tại."""
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=4)
        logging.info(f"Tiến độ đã được lưu: {progress}")
    except Exception as e:
        logging.error(f"Lỗi khi lưu tiến độ: {e}")


def _generate_password_chunk(chars, length, start, chunk_size):
    """Tạo một phần mật khẩu."""
    base = len(chars)
    chunk = []
    for i in range(start, start + chunk_size):
        password = []
        idx = i
        for _ in range(length):
            password.append(chars[idx % base])
            idx //= base
        chunk.append(''.join(reversed(password)))
    return chunk


def _crack_worker(zip_file, chars, length, start_index, total_combinations, chunk_size, stop_flag):
    """Tiến trình làm việc để giải mã mật khẩu ZIP."""
    while start_index < total_combinations:
        passwords = _generate_password_chunk(chars, length, start_index, chunk_size)
        for password in passwords:
            if stop_flag.is_set():
                break
            try:
                with pyzipper.AESZipFile(zip_file, 'r') as zf:
                    zf.extractall(pwd=password.encode('utf-8'))
                return password  # Trả về mật khẩu nếu giải mã thành công
            except (RuntimeError, pyzipper.BadZipFile):
                continue
            except Exception as e:
                logging.error(f"Lỗi không mong muốn: {e}")
        start_index += chunk_size
    return None


def start_cracking(settings):
    """Bắt đầu quá trình giải mã."""
    zip_file = settings["zip_file"]
    max_password_length = settings["max_password_length"]
    chars = settings["character_set"]
    max_processes = settings["max_processes"]
    chunk_size = settings.get("chunk_size", 1000)

    # Kiểm tra đầu vào
    if not zip_file:
        print("Lỗi: Tệp ZIP chưa được đặt.")
        return

    if not _validate_zip_file(zip_file):
        print(f"Lỗi: Tệp ZIP không tồn tại hoặc không hợp lệ: {zip_file}")
        return

    # Tính tổng số tổ hợp cần thử
    total_combinations = sum(len(chars) ** length for length in range(1, max_password_length + 1))
    print(f"Đang thử {total_combinations} tổ hợp mật khẩu với độ dài từ 1 đến {max_password_length}...")

    with multiprocessing.Manager() as manager:
        stop_flag = manager.Event()
        pool = multiprocessing.Pool(max_processes)

        try:
            # Bắt đầu thử mật khẩu từ độ dài 1 đến max_password_length
            for current_length in range(1, max_password_length + 1):
                length_combinations = len(chars) ** current_length

                tasks = [
                    pool.apply_async(
                        _crack_worker,
                        args=(zip_file, chars, current_length, i, length_combinations, chunk_size, stop_flag)
                    )
                    for i in range(0, length_combinations, chunk_size)
                ]

                # Hiển thị tiến trình tổng quát
                for task in tqdm(tasks, total=len(tasks), desc=f"Đang thử mật khẩu độ dài {current_length}"):
                    result = task.get()
                    if result:
                        print(f"Mật khẩu đã giải mã thành công: {result}")
                        logging.info(f"Mật khẩu đã được giải mã thành công: {result}")
                        stop_flag.set()
                        return

        except KeyboardInterrupt:
            print("Quá trình bị gián đoạn bởi người dùng.")
        finally:
            pool.close()
            pool.join()


def interactive_menu():
    """Menu tương tác cho trình giải mã ZIP."""
    settings = {
        "zip_file": None,
        "max_password_length": 1,
        "character_set": "lowercase+digits",
        "max_processes": multiprocessing.cpu_count(),  # Số CPU mặc định
        "chunk_size": 1000
    }

    char_map = {
        "lowercase": string.ascii_lowercase,
        "uppercase": string.ascii_uppercase,
        "digits": string.digits,
        "special": string.punctuation
    }

    while True:
        print("\n[ Trình Giải Mã Mật Khẩu ZIP ]")
        print("1. Cài đặt tham số")
        print("2. Bắt đầu giải mã")
        print("3. Thoát")

        choice = input("Chọn một tùy chọn: ").strip()

        if choice == "1":
            zip_file = input("Nhập đường dẫn tới tệp ZIP: ").strip()
            if os.path.isfile(zip_file):
                settings["zip_file"] = zip_file
            else:
                print("Lỗi: Tệp ZIP không tồn tại.")
                continue

            try:
                max_length = int(input("Nhập độ dài mật khẩu tối đa: ").strip())
                settings["max_password_length"] = max_length
            except ValueError:
                print("Lỗi: Độ dài mật khẩu không hợp lệ.")
                continue

            print("Các bộ ký tự khả dụng: lowercase, uppercase, digits, special")
            chars_input = input("Nhập bộ ký tự (ví dụ: lowercase+digits): ").strip()
            settings["character_set"] = "".join(char_map.get(part, part) for part in chars_input.split("+"))

            settings["chunk_size"] = int(input("Nhập kích thước từng phần (mặc định 1000): ").strip() or 1000)

            # Hiển thị số CPU tối đa và gợi ý
            max_cpus = multiprocessing.cpu_count()
            print(f"Hệ thống của bạn có {max_cpus} CPU khả dụng.")
            suggested_processes = max(1, max_cpus - 1)  # Gợi ý sử dụng tất cả trừ 1 CPU
            print(f"Gợi ý: Sử dụng {suggested_processes} tiến trình để đạt hiệu năng tối đa.")

            try:
                processes = int(input(f"Nhập số tiến trình bạn muốn sử dụng (mặc định {suggested_processes}): ").strip() or suggested_processes)
                if processes > max_cpus or processes < 1:
                    print(f"Lỗi: Số tiến trình phải nằm trong khoảng từ 1 đến {max_cpus}.")
                    continue
                settings["max_processes"] = processes
            except ValueError:
                print("Lỗi: Số tiến trình không hợp lệ.")
                continue

        elif choice == "2":
            if not settings["zip_file"]:
                print("Lỗi: Hãy đặt tệp ZIP trước khi bắt đầu.")
                continue
            start_cracking(settings)

        elif choice == "3":
            print("Đang thoát...")
            break

        else:
            print("Tùy chọn không hợp lệ. Vui lòng thử lại.")


if __name__ == "__main__":
    interactive_menu()
