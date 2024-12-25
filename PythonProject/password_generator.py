import numpy as np

class PasswordGenerator:
    @staticmethod
    def generate_password_chunk_numpy(chars, length, start, end):
        chars = np.array(chars)
        num_chars = len(chars)
        indices = np.arange(start, end)
        passwords = np.empty((end - start, length), dtype="<U1")
        for i in range(length):
            passwords[:, -(i + 1)] = np.take(chars, indices % num_chars)
            indices //= num_chars
        for password in passwords:
            yield ''.join(password)
