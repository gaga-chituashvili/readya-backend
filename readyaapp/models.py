from django.db import models
import uuid

class AudioDocument(models.Model):
    STATUS_CHOICES = (
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
    )
    
    FILE_TYPE_CHOICES = (
        ("pdf", "PDF"),
        ("docx", "Word Document"),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()

    document_file = models.FileField(upload_to="uploads/documents/", null=True, blank=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default="pdf")
    
    mp3_file = models.FileField(upload_to="uploads/mp3/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.email} - {self.file_type} - {self.status}"