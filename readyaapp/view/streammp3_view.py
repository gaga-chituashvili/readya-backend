from readyaapp.models import AudioDocument
from rest_framework.decorators import api_view,permission_classes
from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
@api_view(["GET"])
@permission_classes([AllowAny]) 
def stream_mp3(request, doc_id):
    try:
        doc = AudioDocument.objects.get(id=doc_id)
        if not doc.mp3_file:
            raise Http404

        return FileResponse(
            doc.mp3_file.open("rb"),  # 👈 ეს ჯობია ვიდრე open(path)
            content_type="audio/mpeg"
        )
    except AudioDocument.DoesNotExist:
        raise Http404