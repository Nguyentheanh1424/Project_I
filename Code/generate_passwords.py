import itertools

def generate_passwords(output_file, min_length=6, max_length=8, charset="abcdefghijklmnopqrstuvwxyz0123456789"):
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            for length in range(min_length, max_length + 1):
                for password in itertools.product(charset, repeat=length):
                    f.write("".join(password) + "\n")
        print(f"Đã tạo từ điển mật khẩu tại: {output_file}")
    except Exception as e:
        print(f"Lỗi khi tạo từ điển: {e}")


output_file = "password_dictionary.txt"
min_length = 1
max_length = 3
charset = "012345678abcdefghijklmnopqrstuvwxyz"

generate_passwords(output_file, min_length, max_length, charset)


# import os
#
# # Đường dẫn tệp rác
# file_path = "test_file_1000KB.txt"
#
# # Kích thước tệp mong muốn (1GB = 1024 * 1024 * 1024 bytes)
# file_size = 1 * 1024 * 1000 * 1000
#
# # Tạo tệp với dữ liệu rác
# with open(file_path, "wb") as f:
#     chunk_size = 1024 * 1024  # 1MB mỗi lần ghi
#     written = 0
#     while written < file_size:
#         f.write(os.urandom(chunk_size))  # Ghi dữ liệu ngẫu nhiên
#         written += chunk_size
#
# print(f"Tệp rác {file_path} đã được tạo với kích thước 1GB.")