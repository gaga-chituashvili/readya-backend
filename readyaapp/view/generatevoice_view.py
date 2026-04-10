from rest_framework.decorators import api_view
from rest_framework.response import Response
from readyaapp.models import AudioDocument


@api_view(["POST"])
def generate_voice(request, doc_id):

    try:
        doc = AudioDocument.objects.get(id=doc_id)
    except AudioDocument.DoesNotExist:
        return Response({"error": "Document not found"}, status=404)

    if not doc.mp3_file:
        return Response({"error": "Audio not generated yet"}, status=400)

    return Response({
        "stream_url": request.build_absolute_uri(f"/stream/{doc.id}/"),
        "words": doc.word_timestamps or []
    })