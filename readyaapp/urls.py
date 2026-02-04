from django.urls import path
from .views import UploadPDFView, home
from .views import UploadPDFView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
     path('', home, name='home'),
     path("api/upload-pdf/", UploadPDFView.as_view()),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)




