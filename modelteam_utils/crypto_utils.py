import gzip

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def encrypt_compress_file(input_file, output_file, key_hex):
    with open(input_file, 'rb') as f:
        plaintext = f.read()

    plaintext_gz = compress_data(plaintext)
    ciphertext = encrypt(plaintext_gz, key_hex)

    with open(output_file, 'wb') as f:
        f.write(ciphertext)


def decrypt_decompress_file(input_file, output_file, key_hex):
    with open(input_file, 'rb') as f:
        ciphertext = f.read()

    decrypted_gz = decrypt(ciphertext, key_hex)
    plaintext = decompress_data(decrypted_gz)

    with open(output_file, 'wb') as f:
        f.write(plaintext)


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
