from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import os
import base64


class EncryptedResponse:
    def __init__(self, encrypted_data: str, aes_properties: str):
        self.encrypted_data = encrypted_data
        self.aes_properties = aes_properties


def encrypt_using_public_key(data: str, public_key_string: str) -> str:
    pem_key = f"-----BEGIN PUBLIC KEY-----\n{public_key_string}\n-----END PUBLIC KEY-----"
    public_key = serialization.load_pem_public_key(pem_key.encode())

    encrypted_data = public_key.encrypt(
        data.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return base64.b64encode(encrypted_data).decode()


def encrypt_with_aes(data: str, public_key: str) -> EncryptedResponse:
    aes_key = os.urandom(32)
    iv = os.urandom(16)

    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    encryptor = cipher.encryptor()

    pad_len = 16 - len(data) % 16
    padded = data + chr(pad_len) * pad_len

    encrypted_data = encryptor.update(padded.encode()) + encryptor.finalize()

    aes_properties = (
        base64.b64encode(aes_key).decode()
        + "."
        + base64.b64encode(iv).decode()
    )

    encrypted_aes_properties = encrypt_using_public_key(aes_properties, public_key)

    return EncryptedResponse(
        base64.b64encode(encrypted_data).decode(),
        encrypted_aes_properties,
    )
