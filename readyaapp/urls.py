from django.urls import path
from .views import home, UploadDocumentView, stream_mp3

urlpatterns = [
    path('', home, name='home'),
    path('upload/', UploadDocumentView.as_view(), name='upload_document'),
    path('stream/<uuid:doc_id>/', stream_mp3, name='stream_mp3'),
    # path("payment/create/", CreatePaymentView.as_view()),
    # path("payment/verify/", VerifyPaymentView.as_view()),
    # path("generate-voice/<uuid:doc_id>/", generate_voice),
]


