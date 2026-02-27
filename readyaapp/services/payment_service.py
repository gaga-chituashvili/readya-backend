import requests
from django.conf import settings


def refund_payment(payment_id):
    url = f"{settings.KEEPZ_BASE_URL}/payments/{payment_id}/refund"

    headers = {
        "Authorization": f"Bearer {settings.KEEPZ_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers)

    if response.status_code != 200:
        raise Exception("Refund failed")

    return response.json()