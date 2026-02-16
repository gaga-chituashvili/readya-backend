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
