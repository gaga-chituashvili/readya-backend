import json
import requests
from django.conf import settings
from .keepz_crypto import encrypt_with_aes


def get_keepz_base_url():
    return "https://gateway.keepz.me/ecommerce-service"  

def create_payment(amount, email, order_id, description):
    """Create payment in Keepz"""
    
    # Payload
    payload = {
        "orderId": str(order_id),
        "amount": float(amount),
        "currencyCode": "GEL",
        "description": description,
        "customerEmail": email,
        "successUrl": f"{settings.SITE_URL}/payment-success?order_id={order_id}",
        "failUrl": f"{settings.SITE_URL}/payment-failed?order_id={order_id}",
        "callbackUrl": f"{settings.BACKEND_URL}/keepz/webhook/",
    }

    print("📦 Payment Payload:", json.dumps(payload, indent=2))

    encrypted = encrypt_with_aes(
        json.dumps(payload, separators=(",", ":")),
        public_key=settings.KEEPZ_PUBLIC_KEY,
    )

    body = {
        "integratorId": settings.KEEPZ_INTEGRATOR_ID,
        "identifier": str(order_id),
        "encryptedData": encrypted.encrypted_data,
        "aesProperties": encrypted.aes_properties,
        "aes": True,
    }

    print("🔐 Encrypted Request:", json.dumps(body, indent=2))

    try:
        response = requests.post(
            f"{get_keepz_base_url()}/api/integrator/order",
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=20,
        )

        print(f"📡 Response Status: {response.status_code}")
        print(f"📄 Response Body: {response.text}")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ Keepz API Error: {str(e)}")
        raise Exception(f"Keepz API error: {str(e)}")