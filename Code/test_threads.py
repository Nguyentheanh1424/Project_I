from concurrent.futures import ThreadPoolExecutor
import time

def dummy_task():
    time.sleep(0.1)  # Giả lập tác vụ tốn thời gian I/O

def test_threads(max_threads):
    start = time.time()
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(dummy_task) for _ in range(100)]
        for future in futures:
            future.result()  # Chờ các tác vụ hoàn thành
    end = time.time()
    print(f"Thời gian với {max_threads} luồng: {end - start:.2f} giây")

if __name__ == "__main__":
    # Kiểm tra hiệu suất với các số luồng khác nhau
    for threads in range(1, 16, 1):  # Thử từ 1 đến 16 luồng
        test_threads(threads)
