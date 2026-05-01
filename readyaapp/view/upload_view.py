from pathlib import Path
import os
import threading
import requests
import traceback

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile

from readyaapp.services.voice import generate_voice
from readyaapp.services.email import send_email_with_mp3
from readyaapp.services.pdf_reader import extract_text_from_pdf
from readyaapp.services.docx_reader import extract_text_from_docx
from readyaapp.services.image_reader import extract_text_from_image
from readyaapp.models import AudioDocument


@method_decorator(csrf_exempt, name="dispatch")
class UploadDocumentView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):

        document_id = request.data.get("document_id")

        if not document_id:
            return Response({"error": "document_id is required"}, status=400)

        doc, _ = AudioDocument.objects.get_or_create(
            id=document_id,
            defaults={"email": request.data.get("email")}
        )

        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "Unauthorized"}, status=401)
        

        doc.user = user
        doc.save(update_fields=["email", "user"])

       
        # if not user.has_active_subscription():
        #     return Response({"error": "Payment required"}, status=402)

        email = user.email

        file = request.FILES.get("file")
        text_content = request.data.get("text")
        upload_image = request.FILES.get("upload_image")

        if file and not upload_image:
            ext = file.name.lower().split(".")[-1]
            if ext in ['jpg', 'jpeg', 'png', 'webp']:
                upload_image = file
                file = None

        if not file and not text_content and not upload_image:
            return Response({"error": "file, text or image is required"}, status=400)

        doc.email = email
        doc.save(update_fields=["email"])

        player_url = f"{settings.FRONTEND_URL}/player/{doc.id}"

        try:
            # ===== TEXT =====
            if text_content and not file:
                text = text_content
                doc.file_type = "text"

            # ===== IMAGE =====
            elif upload_image:
                doc.upload_image = upload_image
                doc.file_type = "image"
                doc.save()

                image_path = Path(doc.upload_image.path)
                text = extract_text_from_image(str(image_path))

            # ===== PDF / DOCX =====
            else:
                ext = file.name.lower().split(".")[-1]

                if ext == "pdf":
                    doc.file_type = "pdf"
                elif ext in ["docx", "doc"]:
                    doc.file_type = "docx"
                else:
                    return Response({"error": f"Unsupported file type: {ext}"}, status=400)

                doc.document_file = file
                doc.save()

                doc_path = Path(doc.document_file.path)

                if doc.file_type == "pdf":
                    text = extract_text_from_pdf(str(doc_path))
                else:
                    text = extract_text_from_docx(str(doc_path))

            if not text or not text.strip():
                return Response({"error": "No text extracted"}, status=400)

            data = generate_voice(text)

            if not data or "audio_url" not in data:
                raise ValueError("Invalid response from voice generator")

            audio_url = data.get("audio_url")

            if not audio_url:
                raise ValueError("audio_url is empty")

            filename = audio_url.split("/")[-1]

            # ===== HANDLE AUDIO =====
            if audio_url.startswith("http"):
                response = requests.get(audio_url, timeout=20)

                if response.status_code != 200:
                    raise ValueError(f"Download failed: {response.status_code}")

                doc.mp3_file.save(
                    filename,
                    ContentFile(response.content),
                    save=False
                )
            else:
                temp_path = os.path.join(settings.MEDIA_ROOT, filename)

                if not os.path.exists(temp_path):
                    raise ValueError("Generated file missing")

                with open(temp_path, "rb") as f:
                    doc.mp3_file.save(filename, File(f), save=False)

                os.remove(temp_path)

            # ===== SAVE DATA =====
            doc.text_content = text
            doc.status = "done"
            doc.save()

            # ===== EMAIL (background) =====
            try:
                threading.Thread(
                    target=send_email_with_mp3,
                    args=(email, doc.mp3_file.url),
                    daemon=True
                ).start()
            except Exception:
                pass

            return Response({
                "id": str(doc.id),
                "status": doc.status,
                "file_type": doc.file_type,
                "mp3_url": doc.mp3_file.url,
            }, status=201)

        except Exception as e:
            traceback.print_exc()  # ← დაამატე
            doc.status = "failed"
            doc.error_message = str(e)
            doc.save()

            return Response(
                {"error": "processing failed", "detail": str(e)},
                status=500
            )