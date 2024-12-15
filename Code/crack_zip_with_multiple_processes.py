import os
import json
import signal
import string
import time
import pyzipper
from multiprocessing import Pool, Manager

def validate_inputs(length, processes):
    """Kiểm tra tính hợp lệ của đầu vào"""
    max_threads = os.cpu_count()

    if not isinstance(length, int) or length <= 0:
        print("[!] Độ dài mật khẩu phải là số nguyên dương.")
        return False

    if not isinstance(processes, int) or processes <= 0 or processes > max_threads:
        print(f"[!] Số tiến trình phải nằm trong khoảng từ 1 đến {max_threads}.")
        return False

    return True

def handle_signal():
    """Xử lý tín hiệu ngắt"""
    exit(0)

# Lưu trạng thái giải nén khi dừng
def save_progress(zip_file, current_index, total_passwords, length, chars):
    state = {
        "zip_file": zip_file,
        "current_index": current_index,
        "total_passwords": total_passwords,
        "length": length,
        "chars": chars
    }
    try:
        with open("progress_state.json", "w") as f:
            json.dump(state, f)
    except IOError as e:
        print(f"[!] Lỗi khi lưu trạng thái: {e}")

# Tải trạng thái giải nén trước đó
def load_progress():
    try:
        with open("progress_state.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"[!] Lỗi khi tải trạng thái: {e}")
        return None

def index_to_password(index, length, chars):
    """Chuyển đổi chỉ số thành mật khẩu"""
    base = len(chars)
    password = []
    for _ in range(length):
        password.append(chars[index % base])
        index //= base
    return ''.join(reversed(password))

def try_passwords_from_indices(zip_file, index_start, total_passwords, max_processes, length, stop_flag, chars=string.ascii_letters + string.digits):
    """Thử mật khẩu từ các index được sinh ra theo round-robin."""
    signal.signal(signal.SIGINT, handle_signal)
    for index in range(index_start, total_passwords, max_processes):
        if stop_flag.is_set():
            return
        password = index_to_password(index, length, chars)
        try:
            with pyzipper.AESZipFile(zip_file, 'r') as zf:
                zf.extractall(pwd=password.encode('utf-8'))
            stop_flag.set()
            print(f"[+] Mật khẩu tìm thấy: {password}")
            if os.path.exists("progress_state.json"):
                os.remove("progress_state.json")
            return
        except (RuntimeError, pyzipper.BadZipFile):
            continue
        except Exception as e:
            print(f"[!] Lỗi trong quá trình thử mật khẩu: {e}")
            continue
        finally:
            if index % 1000 == 0:
                save_progress(zip_file, index, total_passwords, length, chars)

def crack_zip_with_index_round_robin(zip_file, length, max_processes, chars=string.ascii_letters + string.digits):
    """Thực hiện thám mã file ZIP bằng cách phân chia công việc kiểu round-robin."""
    total_passwords = len(chars) ** length

    progress = load_progress()
    if progress and progress["zip_file"] == zip_file and length == progress["length"] and chars == progress["chars"]:
        print("[+] Ghi nhận tệp đã từng thực hiện thám mã")
        elapsed = (progress["current_index"] / progress["total_passwords"]) * 100
        print(f"[+] Thực hiện được {elapsed: .2f}% trong quá trình trước đó.")
        while True:
            cmdyn = input("[+] Bạn có muốn tiếp tục không? Y/N: ")
            if cmdyn == "Y":
                index_start = progress["current_index"]
                break
            elif cmdyn == "N":
                os.remove("progress_state.json")
                index_start = 0
                break
            else:
                print("[!] Lệnh không hợp lệ, vui lòng thử lại.")
    else:
        index_start = 0

    print(f"\n[+] Tên tệp: {zip_file}")
    print(f"[+] Độ dài mật khẩu: {length}")
    print(f"[+] Tổng mật khẩu thử: {total_passwords}")
    with Manager() as manager:
        stop_flag = manager.Event()
        start_time = time.time()

        def signal_handler():
            print("\n[!] Phát hiện tín hiệu ngắt. Đang lưu trạng thái...")
            stop_flag.set()
            pool.terminate()
            pool.join()
            exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        try:
            with Pool(processes=max_processes) as pool:
                tasks = [
                    pool.apply_async(
                        try_passwords_from_indices,
                        args=(zip_file, index_start + process_id, total_passwords, max_processes, length, stop_flag, chars)
                    )
                    for process_id in range(max_processes)
                ]
                for task in tasks:
                    if stop_flag.is_set():
                        break
                    task.wait()
        except Exception as e:
            print(f"[!] Lỗi khi tạo tiến trình hoặc thực thi công việc: {e}")
        finally:
            elapsed_time = time.time() - start_time
            if not stop_flag.is_set():
                print("[!] Không tìm thấy mật khẩu.")
                os.remove("progress_state.json")
            print(f"Thời gian thực hiện: {elapsed_time:.2f} giây")

if __name__ == "__main__":
    print("Danh sách yêu cầu:")
    print("1 - Tạo danh sách mật khẩu và thám mã")
    print("2 - Kiểm tra số lượng luồng tối đa")
    print("3 - Thoát")

    max_threads = os.cpu_count()

    try:
        while True:
            cmd = input("Nhập yêu cầu: ")

            if cmd == "1":
                try:
                    length = int(input("Nhập độ dài mật khẩu: "))
                    zip_file = input("Nhập đường dẫn file ZIP: ").strip()

                    if not os.path.exists(zip_file):
                        print("[!] File ZIP không tồn tại.")
                        continue

                    processes = int(input("Nhập số tiến trình sử dụng: "))

                    if not validate_inputs(length, processes):
                        continue

                    crack_zip_with_index_round_robin(zip_file, length, processes,
                                                     chars=string.ascii_lowercase + string.digits)
                except ValueError:
                    print("[!] Vui lòng nhập số hợp lệ.")

            elif cmd == "2":
                print(f"Số tiến trình tối đa là: {max_threads}")

            elif cmd == "3":
                print("[+] Đang thoát chương trình...")
                break

            else:
                print("[!] Lệnh không hợp lệ, vui lòng thử lại.")
    except KeyboardInterrupt:
        print("\n[!] Chương trình bị hủy bởi người dùng.")
