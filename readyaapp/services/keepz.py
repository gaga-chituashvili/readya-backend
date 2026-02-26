import json
import requests
from django.conf import settings
from .keepz_crypto import encrypt_with_aes, decrypt_with_aes


def get_keepz_base_url():
    return "https://gateway.keepz.me/ecommerce-service"



def create_payment(amount, email, order_id, description):

    payload = {
        "amount": amount,
        "receiverId": settings.KEEPZ_RECEIVER_ID,
        "receiverType": "BRANCH",
        "integratorId": settings.KEEPZ_INTEGRATOR_ID,
        "integratorOrderId": str(order_id),
        "currency": "GEL",
        "directLinkProvider": "CREDO",
        "successRedirectUri": f"{settings.SITE_URL}/payment-success?order_id={order_id}",
        "failRedirectUri": f"{settings.SITE_URL}/payment-failed?order_id={order_id}",
        "callbackUri": f"{settings.BACKEND_URL}/keepz/webhook/",
    }


    encrypted = encrypt_with_aes(
        json.dumps(payload, separators=(",", ":")),
        public_key=settings.KEEPZ_PUBLIC_KEY,
    )

    body = {
        "identifier": settings.KEEPZ_INTEGRATOR_ID,
        "encryptedData": encrypted.encrypted_data,
        "encryptedKeys": encrypted.aes_properties,
        "aes": True,
    }

    

    url = f"{get_keepz_base_url()}/api/integrator/order?integratorId={settings.KEEPZ_INTEGRATOR_ID}"

    try:
        response = requests.post(
            url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=20,
        )


        response.raise_for_status()

        data = response.json()

       
        if data.get("encryptedData"):
            decrypted_json = decrypt_with_aes(
                data["encryptedKeys"],
                data["encryptedData"],
                settings.KEEPZ_PRIVATE_KEY,
            )


            return json.loads(decrypted_json)

       
        return data

    except requests.exceptions.RequestException:
        print("❌ Keepz RAW Response:", response.text)
        raise Exception(f"Keepz API error: {response.text}")