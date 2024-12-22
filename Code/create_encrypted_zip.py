import pyzipper


def create_aes_encrypted_zip(zip_filename, files, password):
    """
    Tạo file ZIP được mã hóa bằng AES.

    Args:
        zip_filename (str): Tên file ZIP sẽ được tạo.
        files (list): Danh sách các file cần thêm vào file ZIP.
        password (str): Mật khẩu để mã hóa file ZIP.
    """
    try:
        # Mở file ZIP với chế độ AES mã hóa
        with pyzipper.AESZipFile(zip_filename, 'w', compression=pyzipper.ZIP_DEFLATED,
                                 encryption=pyzipper.WZ_AES) as zf:
            # Đặt mật khẩu cho file ZIP
            zf.setpassword(password.encode())
            # Thêm các file vào file ZIP
            for file in files:
                zf.write(file, arcname=file)
        print(f"[+] File ZIP mã hóa AES được tạo thành công: {zip_filename}")
    except Exception as e:
        print(f"[!] Có lỗi xảy ra: {e}")


# Ví dụ sử dụng
if __name__ == "__main__":
    # Tên file ZIP đầu ra
    zip_filename = "zzz.zip"
    # Danh sách file cần thêm vào ZIP (Đảm bảo các file tồn tại trong thư mục)
    with open("test.txt", "w") as file:
        file.write("hao lo hao lo 123 123.\n")
    files_to_zip = ["test.txt"]  # Thay bằng danh sách file của bạn
    # Mật khẩu cho file ZIP
    password = input("Nhập mật khẩu:")

    create_aes_encrypted_zip(zip_filename, files_to_zip, password)
