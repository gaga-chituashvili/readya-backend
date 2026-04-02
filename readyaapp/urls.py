from django.urls import path
from readyaapp.view.sign_view import LoginView, LogoutView, ProfileView, RegisterView
from .views import   home
from readyaapp.view.upload_view import UploadDocumentView
from readyaapp.view.streammp3_view import stream_mp3
from readyaapp.view.payment_view import create_payment_view, check_payment_status, keepz_webhook
from readyaapp.view.generatevoice_view import generate_voice
from readyaapp.view.openai_view import chat_ai
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('', home, name='home'),
    path('upload/', UploadDocumentView.as_view(), name='upload_document'),
    path('stream/<uuid:doc_id>/', stream_mp3, name='stream_mp3'),
    path('voice/<uuid:doc_id>/', generate_voice, name='generate_voice'),

    # Payment endpoints
    path('payment/create/', create_payment_view, name='create_payment'),
    path('payment/status/<uuid:document_id>/', check_payment_status, name='check_payment_status'),
    path('keepz/webhook/', keepz_webhook, name='keepz_webhook'),
    
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # AI chat endpoints
    path('chat/<uuid:doc_id>/', chat_ai, name='chat_with_ai'),
    path('chat/', chat_ai, name='chat_general_outid'),
   

    # Authentication endpoints
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
