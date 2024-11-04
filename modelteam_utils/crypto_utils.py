import gzip
import hashlib

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def compress_file(input_file, output_file):
    with open(input_file, 'rb') as f:
        data = f.read()

    compressed_data = compress_data(data)

    with open(output_file, 'wb') as f:
        f.write(compressed_data)


def encrypt(data, key_hex):
    key = bytes.fromhex(key_hex)
    iv = b'\x00' * 16
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv),
                    backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()
    return ciphertext


def decrypt(data, key_hex):
    key = bytes.fromhex(key_hex)
    iv = b'\x00' * 16
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv),
                    backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(data) + decryptor.finalize()
    return plaintext


def compress_data(data):
    compressed_data = gzip.compress(data)
    return compressed_data


def decompress_data(data):
    decompressed_data = gzip.decompress(data)
    return decompressed_data


def generate_hc(file_path, hash_algorithm='sha256'):
    hash_func = hashlib.new(hash_algorithm)
    with open(file_path, 'rb') as file:
        while chunk := file.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()