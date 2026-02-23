from django.urls import path
from .views import home, UploadDocumentView, stream_mp3
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('', home, name='home'),
    path('upload/', UploadDocumentView.as_view(), name='upload_document'),
    path('stream/<uuid:doc_id>/', stream_mp3, name='stream_mp3'),
    # path("payment/create/", CreatePaymentView.as_view()),
    # path("payment/verify/", VerifyPaymentView.as_view()),
    # path("generate-voice/<uuid:doc_id>/", generate_voice),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
