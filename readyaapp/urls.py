from django.urls import path
from .views import UploadPDFView, home, stream_mp3
from .views import UploadPDFView


urlpatterns = [
     path('', home, name='home'),
     path("api/upload-pdf/", UploadPDFView.as_view()),
      path("audio/<uuid:doc_id>/", stream_mp3),
]

