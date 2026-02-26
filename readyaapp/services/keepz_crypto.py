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


# 🔐 RSA ENCRYPT (AES key + IV)
def encrypt_using_public_key(data: str, public_key_string: str) -> str:
    public_key = serialization.load_pem_public_key(
        public_key_string.encode()
    )

    encrypted_data = public_key.encrypt(
        data.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return base64.b64encode(encrypted_data).decode()


# 🔓 RSA DECRYPT (AES key + IV)
def decrypt_using_private_key(encrypted_data: str, private_key_string: str) -> str:
    private_key = serialization.load_pem_private_key(
        private_key_string.encode(),
        password=None
    )

    decrypted_data = private_key.decrypt(
        base64.b64decode(encrypted_data),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return decrypted_data.decode()


# 🔐 HYBRID ENCRYPT (AES + RSA)
def encrypt_with_aes(data: str, public_key: str) -> EncryptedResponse:

    aes_key = os.urandom(32)
    iv = os.urandom(16)

    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    encryptor = cipher.encryptor()

    padder = sym_padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()

    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    aes_properties = (
        base64.b64encode(aes_key).decode()
        + "."
        + base64.b64encode(iv).decode()
    )

    encrypted_aes_properties = encrypt_using_public_key(
        aes_properties,
        public_key,
    )

    return EncryptedResponse(
        encrypted_data=base64.b64encode(encrypted_data).decode(),
        aes_properties=encrypted_aes_properties,
    )


# 🔓 HYBRID DECRYPT (AES + RSA)
def decrypt_with_aes(encrypted_keys: str, encrypted_data: str, private_key: str) -> str:

    decrypted_properties = decrypt_using_private_key(
        encrypted_keys,
        private_key
    )

    aes_key_b64, iv_b64 = decrypted_properties.split(".")
    aes_key = base64.b64decode(aes_key_b64)
    iv = base64.b64decode(iv_b64)

    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    decryptor = cipher.decryptor()

    decrypted_padded = decryptor.update(base64.b64decode(encrypted_data)) + decryptor.finalize()

    pad_length = decrypted_padded[-1]
    decrypted = decrypted_padded[:-pad_length]

    return decrypted.decode()