import os
import base64
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class EncryptedResponse:
    def __init__(self, encrypted_data: str, aes_properties: str):
        self.encrypted_data = encrypted_data
        self.aes_properties = aes_properties


def encrypt_using_public_key(data: str, public_key_string: str) -> str:
    """RSA encryption with public key (PKCS1v15 REQUIRED by Keepz)"""

    public_key = serialization.load_pem_public_key(
        public_key_string.encode()
    )

    encrypted_data = public_key.encrypt(
        data.encode(),
        padding.PKCS1v15()   # ✅ IMPORTANT FIX
    )

    return base64.b64encode(encrypted_data).decode()


def encrypt_with_aes(data: str, public_key: str) -> EncryptedResponse:
    """AES + RSA hybrid encryption (Keepz compatible)"""

    # Generate random AES key (256-bit) and IV (128-bit)
    aes_key = os.urandom(32)
    iv = os.urandom(16)

    # AES-CBC encryption
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    encryptor = cipher.encryptor()

    # PKCS7 padding for AES
    padder = sym_padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()

    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Combine AES key and IV (base64.key + "." + base64.iv)
    aes_properties = (
        base64.b64encode(aes_key).decode()
        + "."
        + base64.b64encode(iv).decode()
    )

    # Encrypt AES key+IV using RSA (PKCS1v15)
    encrypted_aes_properties = encrypt_using_public_key(
        aes_properties,
        public_key,
    )

    return EncryptedResponse(
        encrypted_data=base64.b64encode(encrypted_data).decode(),
        aes_properties=encrypted_aes_properties,
    )