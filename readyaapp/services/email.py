from django.core.mail import EmailMessage
from django.conf import settings
import os

def send_email_with_mp3(to_email: str, mp3_path: str):
    print("EMAIL FUNCTION STARTED")
    print("TO:", to_email)
    print("FILE EXISTS:", os.path.exists(mp3_path))
    print("FILE SIZE:", os.path.getsize(mp3_path) if os.path.exists(mp3_path) else "NO FILE")

    email = EmailMessage(
        subject="Test from Readya",
        body="Audio generated successfully",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )

    # დროებით attachment ამოიღე
    # email.attach_file(mp3_path)

    result = email.send(fail_silently=False)

    print("EMAIL SEND RESULT:", result)

    return {"status": "sent"}
