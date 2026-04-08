import email
import os
from pydoc import doc
import threading
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from readyaapp.services.cartesia_tts import text_to_mp3
from readyaapp.services.email import send_email_with_mp3
from readyaapp.services.pdf_reader import extract_text_from_pdf
from readyaapp.services.docx_reader import extract_text_from_docx
from readyaapp.services.image_reader import extract_text_from_image

from ..models import AudioDocument

from pydub import AudioSegment


# ===== HELPERS =====
def split_text(text: str, size: int = 800):
    return [text[i:i + size] for i in range(0, len(text), size)]


def generate_chunk_mp3(chunk, mp3_dir, speed, voice_id):
    filename = f"{uuid4()}.mp3"
    path = mp3_dir / filename

    text_to_mp3(
        chunk,
        str(path),
        speed=speed,
        voice_id=voice_id
    )

    return path


@method_decorator(csrf_exempt, name="dispatch")
class UploadDocumentView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):

        speed = float(request.data.get("speed", 0.92))
        voice_id = request.data.get("voice_id")

        document_id = request.data.get("document_id")

        if not document_id:
            return Response({"error": "document_id is required"}, status=400)

        try:
            doc, _ = AudioDocument.objects.get_or_create(
                id=document_id,
                defaults={"email": request.data.get("email")}
            )
        except AudioDocument.DoesNotExist:
            return Response({"error": "Document not found"}, status=404)

        user = request.user

        if not user or not user.is_authenticated:
            return Response({"error": "Unauthorized"}, status=401)
        
        email = user.email
        
        # ===== PAYMENT CHECK =====

        if user.credits <= 0 and doc.payment_status != "paid":
            return Response({"error": "Payment required"}, status=402)

        if doc.payment_status != "paid":
            user.credits -= 1
            user.save() 

        file = request.FILES.get("file")
        text_content = request.data.get("text")
        upload_image = request.FILES.get("upload_image")

        if file and not upload_image:
            file_extension = file.name.lower().split(".")[-1]
            if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                upload_image = file
                file = None

        if not file and not text_content and not upload_image:
            return Response({"error": "file, text or image is required"}, status=400)

        doc.email = email
        doc.save(update_fields=["email"])

        player_url = f"{settings.FRONTEND_URL}/player/{doc.id}"

        # ===== IMAGE =====
        if upload_image:
            doc.upload_image = upload_image
            doc.file_type = "image"
            doc.status = "processing"
            doc.save()

            try:
                image_path = Path(doc.upload_image.path)
                text = extract_text_from_image(str(image_path))

                if not text.strip():
                    raise ValueError("No text found in image")

                mp3_filename = f"{uuid4()}.mp3"
                mp3_dir = Path(settings.MEDIA_ROOT) / "uploads/mp3"
                mp3_dir.mkdir(parents=True, exist_ok=True)
                mp3_path = mp3_dir / mp3_filename

                text_to_mp3(text, str(mp3_path), speed=speed, voice_id=voice_id)

                doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
                doc.text_content = text
                doc.status = "done"
                doc.save()

                threading.Thread(
                    target=send_email_with_mp3,
                    args=(email, str(mp3_path), player_url),
                    daemon=True
                ).start()

            except Exception as e:
                doc.status = "failed"
                doc.error_message = str(e)
                doc.save()
                return Response({"error": "processing failed", "detail": str(e)}, status=500)

            return Response({
                "id": str(doc.id),
                "status": doc.status,
                "file_type": doc.file_type,
                "mp3_url": doc.mp3_file.url,
            }, status=201)

        # ===== TEXT (🔥 OPTIMIZED) =====
        if text_content and not file:

            doc.file_type = "text"
            doc.text_content = text_content
            doc.status = "processing"
            doc.save()

            try:
                if not text_content.strip():
                    raise ValueError("Text content is empty")

                if len(text_content) > 5000:
                    raise ValueError("Text exceeds 5000 characters limit")

                mp3_filename = f"{uuid4()}.mp3"
                mp3_dir = Path(settings.MEDIA_ROOT) / "uploads/mp3"
                mp3_dir.mkdir(parents=True, exist_ok=True)
                mp3_path = mp3_dir / mp3_filename

                
                chunks = split_text(text_content, size=400)

                temp_files = []

                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [
                        executor.submit(generate_chunk_mp3, chunk, mp3_dir, speed, voice_id)
                        for chunk in chunks
                    ]

                    for future in as_completed(futures):
                        temp_files.append(future.result())

                # 🔥 merge
                combined = AudioSegment.empty()

                temp_files = sorted(temp_files, key=lambda x: str(x))

                for file_path in temp_files:
                    combined += AudioSegment.from_mp3(file_path)

                combined.export(str(mp3_path), format="mp3")

                # cleanup
                for f in temp_files:
                    try:
                        os.remove(f)
                    except:
                        pass

                doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
                doc.status = "done"
                doc.save()

                threading.Thread(
                    target=send_email_with_mp3,
                    args=(email, str(mp3_path), player_url),
                    daemon=True
                ).start()

            except Exception as e:
                doc.status = "failed"
                doc.error_message = str(e)
                doc.save()
                return Response({"error": "processing failed", "detail": str(e)}, status=500)

            return Response({
                "id": str(doc.id),
                "status": doc.status,
                "file_type": doc.file_type,
                "mp3_url": doc.mp3_file.url,
            }, status=201)

        # ===== PDF / DOCX =====
        file_extension = file.name.lower().split(".")[-1]

        if file_extension == "pdf":
            file_type = "pdf"
        elif file_extension in ["docx", "doc"]:
            file_type = "docx"
        else:
            return Response({"error": f"Unsupported file type: {file_extension}"}, status=400)

        doc.document_file = file
        doc.file_type = file_type
        doc.status = "processing"
        doc.save()

        try:
            doc_path = Path(doc.document_file.path)

            if file_type == "pdf":
                text = extract_text_from_pdf(str(doc_path))
            else:
                text = extract_text_from_docx(str(doc_path))

            if not text.strip():
                raise ValueError("No text extracted")

            mp3_filename = f"{uuid4()}.mp3"
            mp3_path = Path(settings.MEDIA_ROOT) / "uploads/mp3" / mp3_filename
            mp3_path.parent.mkdir(parents=True, exist_ok=True)

            text_to_mp3(text, str(mp3_path), speed=speed, voice_id=voice_id)

            doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
            doc.status = "done"
            doc.save()

            threading.Thread(
                target=send_email_with_mp3,
                args=(email, str(mp3_path), player_url),
                daemon=True
            ).start()

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)
            doc.save()
            return Response({"error": "processing failed", "detail": str(e)}, status=500)

        return Response({
            "id": str(doc.id),
            "status": doc.status,
            "file_type": doc.file_type,
            "mp3_url": doc.mp3_file.url,
        }, status=201)