import os
import base64
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class EncryptedResponse:
    def __init__(self, encrypted_data: str, aes_properties: str):
        self.encrypted_data = encrypted_data
        self.aes_properties = aes_properties


def encrypt_using_public_key(data: str, public_key_string: str) -> str:
    """RSA encryption with public key"""
    public_key = serialization.load_pem_public_key(
        public_key_string.encode()
    )

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
    """AES + RSA hybrid encryption"""
    
    # Generate random AES key and IV
    aes_key = os.urandom(32)
    iv = os.urandom(16)

    # AES encryption
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    encryptor = cipher.encryptor()

    # Padding
    padder = sym_padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()

    # Encrypt data
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # Combine AES key + IV
    aes_properties = (
        base64.b64encode(aes_key).decode()
        + "."
        + base64.b64encode(iv).decode()
    )

    # RSA encrypt the AES properties
    encrypted_aes_properties = encrypt_using_public_key(
        aes_properties,
        public_key,
    )

    return EncryptedResponse(
        encrypted_data=base64.b64encode(encrypted_data).decode(),
        aes_properties=encrypted_aes_properties,
    )