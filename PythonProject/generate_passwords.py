import itertools


def generate_passwords(output_file, min_length=6, max_length=8, charset="abcdefghijklmnopqrstuvwxyz0123456789"):
    """
    Tạo tệp từ điển mật khẩu dựa trên charset và độ dài mật khẩu.

    Args:
        output_file (str): Đường dẫn tệp để lưu từ điển mật khẩu.
        min_length (int): Độ dài mật khẩu tối thiểu.
        max_length (int): Độ dài mật khẩu tối đa.
        charset (str): Bộ ký tự để tạo mật khẩu.
    """
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            for length in range(min_length, max_length + 1):
                for password in itertools.product(charset, repeat=length):
                    f.write("".join(password) + "\n")
        print(f"Đã tạo từ điển mật khẩu tại: {output_file}")
    except Exception as e:
        print(f"Lỗi khi tạo từ điển: {e}")


output_file = "password_dictionary.txt"
min_length = 3  # Độ dài mật khẩu tối thiểu
max_length = 3  # Độ dài mật khẩu tối đa
charset = "abcdefghijklmnopqrstuvwxyz0123456789"

generate_passwords(output_file, min_length, max_length, charset)
