from django.db import models
import uuid
import os

class AudioDocument(models.Model):
    STATUS_CHOICES = (
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
        ("pending_payment", "Pending Payment"),
    )

    FILE_TYPE_CHOICES = (
        ("pdf", "PDF"),
        ("docx", "Word Document"),
        ("text", "Plain Text"),
        ("image", "Image"),
    )

    # PAYMENT_STATUS_CHOICES = (
    #     ("pending", "Pending"),
    #     ("paid", "Paid"),
    #     ("failed", "Failed"),
    # )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()

    document_file = models.FileField(upload_to="uploads/documents/", null=True, blank=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default="pdf")

    text_content = models.TextField(blank=True, null=True)
    upload_image = models.ImageField(upload_to="uploads/images/", null=True, blank=True)

    mp3_file = models.FileField(upload_to="uploads/mp3/", null=True, blank=True)

    word_timestamps = models.JSONField(null=True, blank=True)


    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")

    # payment_status = models.CharField(
    #     max_length=20,
    #     choices=PAYMENT_STATUS_CHOICES,
    #     default="pending"
    # )

    # payment_amount = models.DecimalField(
    #     max_digits=10,
    #     decimal_places=2,
    #     null=True,
    #     blank=True
    # )

    # payment_id = models.CharField(
    #     max_length=255,
    #     null=True,
    #     blank=True
    # )

    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        if self.document_file and os.path.isfile(self.document_file.path):
           self.document_file.delete(save=False)

        if self.upload_image and os.path.isfile(self.upload_image.path):
           self.upload_image.delete(save=False)

        if self.mp3_file and os.path.isfile(self.mp3_file.path):
           self.mp3_file.delete(save=False)

        super().delete(*args, **kwargs)


    def __str__(self):
        return f"{self.email} - {self.file_type} - {self.status}"



