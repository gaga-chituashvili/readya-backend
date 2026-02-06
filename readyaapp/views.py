
# Create your views here.

from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to readya  Dashboard!")


from pathlib import Path
from uuid import uuid4

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import AudioDocument
from .services.pdf_reader import extract_text_from_pdf
from .services.azure import text_to_mp3


@method_decorator(csrf_exempt, name="dispatch")
class UploadPDFView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        pdf = request.FILES.get("file")
        email = request.data.get("email")

        if not pdf:
            return Response({"error": "file is required"}, status=400)
        if not email:
            return Response({"error": "email is required"}, status=400)

        doc = AudioDocument.objects.create(
            email=email,
            pdf_file=pdf,
            status="processing",
        )

        try:
            pdf_path = Path(doc.pdf_file.path)

            text = extract_text_from_pdf(str(pdf_path))
            if not text.strip():
                raise ValueError("No extractable text found in PDF")

            mp3_filename = f"{uuid4()}.mp3"
            mp3_path = pdf_path.parent.parent / "mp3" / mp3_filename
            mp3_path.parent.mkdir(parents=True, exist_ok=True)

            # 🔊 TTS
            text_to_mp3(text, str(mp3_path))

            # 💾 DB save
            doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
            doc.status = "done"
            doc.save()

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)
            doc.save()

            return Response(
                {"error": "processing failed", "detail": str(e)},
                status=500,
            )

        return Response(
            {
                "id": str(doc.id),
                "status": doc.status,
                "mp3_url": doc.mp3_file.url,
            },
            status=201,
        )
