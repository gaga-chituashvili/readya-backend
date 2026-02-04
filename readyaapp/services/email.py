import base64, os, requests
from django.conf import settings

def send_email_with_mp3(to_email: str, mp3_path: str):
    with open(mp3_path, "rb") as f:
        mp3_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": "თქვენი აუდიო მზადაა",
        "text": "PDF წარმატებით გადაიქცა ხმოვან ფაილად — readya.me",
        "attachments": [{
            "filename": os.path.basename(mp3_path),
            "content": mp3_b64,
        }],
    }

    r = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    r.raise_for_status()
    return r.json()
