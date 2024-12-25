import numpy as np

class PasswordGenerator:
    @staticmethod
    def generate_password_chunk_numpy(chars, length, start, end):
        """
        Tạo một chunk mật khẩu từ danh sách ký tự, độ dài cố định,
        từ chỉ số bắt đầu-kết thúc trong danh sách tổ hợp có thể sinh.

        Args:
            chars (list): Danh sách ký tự để tạo mật khẩu.
            length (int): Độ dài mật khẩu cố định.
            start (int): Chỉ số bắt đầu.
            end (int): Chỉ số kết thúc.

        Yields:
            str: Từng mật khẩu được tạo ra trong chunk, dưới dạng String.
        """
        # Chuyển danh sách ký tự thành mảng NumPy để tối ưu hiệu suất
        chars = np.array(chars)

        # Xác định tổng số ký tự trong danh sách
        num_chars = len(chars)

        # Tạo mảng chỉ số từ start đến end (không bao gồm end)
        indices = np.arange(start, end)

        # Tạo mảng rỗng để lưu mật khẩu
        # Mảng có kích thước (số lượng mật khẩu, độ dài mật khẩu), dtype="<U1" là chuỗi 1 ký tự
        passwords = np.empty((end - start, length), dtype="<U1")

        # Vòng lặp qua từng vị trí trong mật khẩu (từ phải sang trái)
        for i in range(length):
            # Lấy ký tự tại vị trí hiện tại
            # `indices % num_chars`: Xác định chỉ số ký tự từ danh sách `chars`
            passwords[:, -(i + 1)] = np.take(chars, indices % num_chars)

            # Giảm chỉ số (`indices`) để xử lý cho vị trí tiếp theo (chia đều cho num_chars)
            indices //= num_chars

        # Lặp qua từng mật khẩu đã tạo và trả về dưới dạng chuỗi
        for password in passwords:
            # Kết hợp các ký tự trong mảng thành một chuỗi
            yield ''.join(password)
