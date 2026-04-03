from django.contrib import admin
from .models import AudioDocument, SubscriptionPlan



@admin.register(AudioDocument)
class AudioDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "file_type", "status", "created_at")
    list_filter = ("status", "file_type", "created_at")
    search_fields = ("email", "id")




@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "duration_days")
    search_fields = ("name",)