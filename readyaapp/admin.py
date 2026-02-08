from django.contrib import admin
from readyaapp.models import AudioDocument



@admin.register(AudioDocument)
class AudioDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "file_type", "status", "created_at")
    list_filter = ("status", "file_type", "created_at")
    search_fields = ("email", "id")