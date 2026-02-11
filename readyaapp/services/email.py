from django.core.mail import EmailMessage
from django.conf import settings

def send_email_with_mp3(to_email: str, mp3_path: str):
    email = EmailMessage(
        subject="🎧 Your audio is ready — Readya",
        body="PDF successfully converted to audio file — readya.me",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )

    email.attach_file(mp3_path)
    email.send(fail_silently=False)

    return {"status": "sent"}



