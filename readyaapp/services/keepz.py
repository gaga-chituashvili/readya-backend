import json
import requests
from django.conf import settings
from .keepz_crypto import encrypt_with_aes


def create_payment(amount, email, order_id, description):

    payload = {
        "orderId": order_id,
        "amount": amount,
        "currencyCode": "GEL",
        "description": description,
        "customerEmail": email,
        "successUrl": f"{settings.SITE_URL}/payment-success?order_id={order_id}",
        "failUrl": f"{settings.SITE_URL}/payment-failed",
        "callbackUrl": f"{settings.BACKEND_URL}/keepz/webhook/",
    }

    encrypted = encrypt_with_aes(
        json.dumps(payload),
        public_key=settings.KEEPZ_PUBLIC_KEY,
    )

    body = {
        "integratorId": settings.KEEPZ_INTEGRATOR_ID,
        "identifier": order_id,
        "encryptedData": encrypted.encrypted_data,
        "aesProperties": encrypted.aes_properties,
        "aes": True,
    }

    response = requests.post(
        "https://gateway.keepz.me/ecommerce-service/api/integrator/order",
        json=body,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    response.raise_for_status()

    return response.json()



import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from django.conf import settings


def generate_signature(payload: dict) -> str:
   
    payload_str = json.dumps(payload, separators=(",", ":"))

    
    private_key = serialization.load_pem_private_key(
        settings.KEEPZ_PRIVATE_KEY.encode(),
        password=None
    )

    
    signature = private_key.sign(
        payload_str.encode(),  
        padding.PKCS1v15(),
        hashes.SHA256()
    )


    return base64.b64encode(signature).decode()




from pathlib import Path
from django.conf import settings

def encrypt_payload(payload: dict) -> str:
    payload_str = json.dumps(payload, separators=(",", ":"))

    key_path = Path(settings.BASE_DIR) / "keys" / "keepz_public.pem"

    public_key = serialization.load_pem_public_key(
        key_path.read_bytes()
    )

    encrypted = public_key.encrypt(
        payload_str.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return base64.b64encode(encrypted).decode()
