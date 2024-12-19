import os
import logging
import string
import multiprocessing
import json
import pyzipper
import sys

# Đặt mã hóa UTF-8 để hỗ trợ tiếng Việt
sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình Logging
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


def _save_progress(progress, settings):
    """Lưu tiến độ hiện tại."""
    progress.update({
        "zip_file": settings["zip_file"],
        "max_password_length": settings["max_password_length"],
        "character_set": settings["character_set"]
    })
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, indent=4)
        logging.info(f"Tiến độ đã được lưu: {progress}")
    except Exception as e:
        logging.error(f"Lỗi khi lưu tiến độ: {e}")


def _load_progress():
    """Tải tiến độ đã lưu."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Lỗi khi tải tiến độ: {e}")
    return None


def _delete_progress():
    """Xóa file tiến độ."""
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        logging.info("File tiến độ đã được xóa.")


def _generate_password_chunk(chars, length, start, chunk_size):
    """Tạo một đoạn mật khẩu."""
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
    """Thám mã tệp ZIP."""
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


def _check_progress_against_settings(settings):
    """Kiểm tra tiến trình lưu trữ."""
    progress = _load_progress()
    if not progress:
        return None

    # So sánh thông tin
    if (
        settings["zip_file"] == progress.get("zip_file") and
        settings["max_password_length"] == progress.get("max_password_length") and
        settings["character_set"] == progress.get("character_set")
    ):
        return progress
    return None


def start_cracking(settings):
    """Thám mã."""
    zip_file = settings["zip_file"]
    max_password_length = settings["max_password_length"]
    chars = settings["character_set"]
    max_processes = settings["max_processes"]
    chunk_size = 1000  # Giá trị mặc định của đoạn

    # Kiểm tra đầu vào
    if not zip_file:
        print("Lỗi: Tệp ZIP chưa được đặt.")
        return

    if not _validate_zip_file(zip_file):
        print(f"Lỗi: Tệp ZIP không tồn tại hoặc không hợp lệ: {zip_file}")
        return

    # Kiểm tra tiến trình lưu trữ
    progress = _check_progress_against_settings(settings)
    if progress:
        print("Tìm thấy tiến trình đã lưu, bạn có muốn tiếp tục không? (y/n)")
        choice = input().strip().lower()
        if choice != "y":
            _delete_progress()
            progress = {"current_length": 1, "current_index": 0}
    else:
        progress = {"current_length": 1, "current_index": 0}

    current_length = progress["current_length"]
    start_index = progress["current_index"]

    # Tính tổng số tổ hợp cần thử
    total_combinations = sum(len(chars) ** length for length in range(1, max_password_length + 1))
    print(f"Đang thử {total_combinations} tổ hợp mật khẩu với độ dài từ 1 đến {max_password_length}...")

    with multiprocessing.Manager() as manager:
        stop_flag = manager.Event()
        pool = multiprocessing.Pool(max_processes)

        try:
            while current_length <= max_password_length:
                length_combinations = len(chars) ** current_length

                print(f"Đang thử mật khẩu độ dài {current_length} ({length_combinations} tổ hợp)...")

                tasks = [
                    pool.apply_async(
                        _crack_worker,
                        args=(zip_file, chars, current_length, i, length_combinations, chunk_size, stop_flag)
                    )
                    for i in range(start_index, length_combinations, chunk_size)
                ]

                for i, task in enumerate(tasks):
                    result = task.get()  # Chờ kết quả của task
                    # Lưu tiến trình mỗi khi hoàn thành một chunk
                    _save_progress({
                        "current_length": current_length,
                        "current_index": (i + 1) * chunk_size
                    }, settings)
                    if result:
                        print(f"Mật khẩu đã giải mã thành công: {result}")
                        logging.info(f"Mật khẩu đã được giải mã thành công: {result}")
                        stop_flag.set()
                        _delete_progress()
                        return

                # Hoàn thành độ dài hiện tại, chuyển sang độ dài tiếp theo
                current_length += 1
                start_index = 0

        except KeyboardInterrupt:
            # Lưu tiến trình khi bị gián đoạn
            print("\nQuá trình bị gián đoạn. Đang lưu tiến độ...")
            _save_progress({"current_length": current_length, "current_index": start_index}, settings)
        finally:
            pool.close()
            pool.join()

    # Nếu không tìm thấy mật khẩu
    print("Không tìm thấy mật khẩu sau khi thử tất cả tổ hợp.")
    logging.info("Không tìm thấy mật khẩu sau khi thử tất cả tổ hợp.")
    _delete_progress()


def interactive_menu():
    """Menu tương tác cho trình giải mã ZIP."""
    settings = {
        "zip_file": None,
        "max_password_length": 1,
        "character_set": "lowercase+digits",
        "max_processes": multiprocessing.cpu_count(),
    }

    char_map = {
        "lowercase": string.ascii_lowercase,
        "uppercase": string.ascii_uppercase,
        "digits": string.digits,
        "special": string.punctuation
    }

    while True:
        print("\n[ Trình Giải Mã Mật Khẩu ZIP ]")
        print("1. Cài đặt tham số và thám mã")
        print("2. Thoát")

        choice = input("Chọn một tùy chọn: ").strip()

        if choice == "1":
            zip_file = input("Nhập đường dẫn tới tệp ZIP: ").strip()
            if not os.path.isfile(zip_file):
                print("Lỗi: Tệp ZIP không tồn tại.")
                continue

            try:
                max_length = int(input("Nhập độ dài mật khẩu tối đa: ").strip())
            except ValueError:
                print("Lỗi: Độ dài mật khẩu không hợp lệ.")
                continue

            print("Các bộ ký tự khả dụng: lowercase, uppercase, digits, special")
            chars_input = input("Nhập bộ ký tự (ví dụ: lowercase+digits): ").strip()
            chars = "".join(char_map.get(part, part) for part in chars_input.split("+"))

            # Cập nhật settings
            settings["zip_file"] = zip_file
            settings["max_password_length"] = max_length
            settings["character_set"] = chars

            # Hiển thị số CPU tối đa và gợi ý tối ưu
            max_cpus = multiprocessing.cpu_count()
            suggested_processes = max(1, max_cpus - 1 if max_cpus <= 4 else int(max_cpus * 0.75))
            print(f"Hệ thống của bạn có {max_cpus} CPU khả dụng.")
            print(f"Gợi ý: Sử dụng {suggested_processes} tiến trình để đạt hiệu năng cao mà không tiêu tốn quá nhiều tài nguyên.")

            try:
                processes = int(input(f"Nhập số tiến trình bạn muốn sử dụng (mặc định {suggested_processes}): ").strip() or suggested_processes)
                if processes > max_cpus or processes < 1:
                    print(f"Lỗi: Số tiến trình phải nằm trong khoảng từ 1 đến {max_cpus}.")
                    continue
                settings["max_processes"] = processes
            except ValueError:
                print("Lỗi: Số tiến trình không hợp lệ.")
                continue

            start_cracking(settings)

        elif choice == "2":
            print("Đang thoát...")
            break

        else:
            print("Tùy chọn không hợp lệ. Vui lòng thử lại.")


if __name__ == "__main__":
    interactive_menu()
