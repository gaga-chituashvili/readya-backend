import requests
from django.core.mail import EmailMessage
from django.conf import settings

def send_email_with_mp3(to_email: str, mp3_url: str):
    email = EmailMessage(
        subject="🎧 Your audio is ready — Readya",
        body="PDF successfully converted to audio file 🎉\n\nMP3 is attached below.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )

    try:
        response = requests.get(mp3_url, timeout=30)
        if response.status_code == 200:
            email.attach("audio.mp3", response.content, "audio/mpeg")
    except Exception:
        pass

    email.send(fail_silently=False)
    return {"status": "sent"}