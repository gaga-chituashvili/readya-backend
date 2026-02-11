from django.core.mail import send_mail

send_mail(
    subject="Local Test Email",
    message="ეს არის ლოკალური ტესტი",
    from_email=None,
    recipient_list=["gagachituashvili7@gmail.com"],
    fail_silently=False,
)
