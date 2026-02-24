from django.urls import path
from .views import check_payment_status, create_payment_view, home, UploadDocumentView, keepz_webhook, stream_mp3
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('', home, name='home'),
    path('upload/', UploadDocumentView.as_view(), name='upload_document'),
    path('stream/<uuid:doc_id>/', stream_mp3, name='stream_mp3'),

    path('payment/create/', create_payment_view, name='create_payment'),
    path('payment/status/<uuid:document_id>/', check_payment_status, name='check_payment_status'),
    path('keepz/webhook/', keepz_webhook, name='keepz_webhook'),
    
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
