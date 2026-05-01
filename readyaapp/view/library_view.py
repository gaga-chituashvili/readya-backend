from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from readyaapp.models import AudioDocument
from django.conf import settings

class UserDocumentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        docs = AudioDocument.objects.filter(
            user=request.user
        ).order_by("-created_at")

        data = [
            {
                "id": str(doc.id),
                "file_type": doc.file_type,
                "status": doc.status,
                "created_at": doc.created_at,
                "mp3_url": doc.mp3_file.url if doc.mp3_file else None,
                "text_preview": doc.text_content[:80] if doc.text_content else None,
            }
            for doc in docs
        ]

        return Response(data)





class DocumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        try:
            doc = AudioDocument.objects.get(id=doc_id, user=request.user)
        except AudioDocument.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        return Response({
            "id": str(doc.id),

           
            "stream_url": f"{settings.BACKEND_URL}/stream/{doc.id}/",

           
            "mp3_url": doc.mp3_file.url if doc.mp3_file else None,

            "words": doc.word_timestamps or [],
            "status": doc.status,
            "file_type": doc.file_type,
        })