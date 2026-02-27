import requests
from django.conf import settings


def refund_payment(payment_id: str) -> dict:
    if not payment_id:
        raise ValueError("payment_id is required for refund")

    url = f"{settings.KEEPZ_BASE_URL}/payments/{payment_id}/refund"

    headers = {
        "Authorization": f"Bearer {settings.KEEPZ_PRIVATE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

    except requests.RequestException as e:
        raise Exception(f"Keepz refund failed: {str(e)}")

    return response.json()