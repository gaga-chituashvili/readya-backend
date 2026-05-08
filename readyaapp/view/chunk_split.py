import threading

import os

from pathlib import Path

from django.core.files import File
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from readyaapp.models import AudioDocument, AudioDocumentChunk
from readyaapp.services.voice import generate_voice
from readyaapp.services.pdf_reader import extract_text_from_pdf
from readyaapp.services.docx_reader import extract_text_from_docx
from readyaapp.services.image_reader import extract_text_from_image
from rest_framework.decorators import api_view

CHUNK_SIZE = 50


def split_into_chunks(text: str, size: int) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i+size]) for i in range(0, len(words), size)]


def generate_and_save_chunk(doc: AudioDocument, chunk_text: str, index: int):
    chunk = AudioDocumentChunk.objects.get_or_create(
        document=doc, index=index
    )[0]

    try:
        data = generate_voice(chunk_text)

        file_path = data["file_path"]
        filename = data["filename"]

        with open(file_path, "rb") as f:
            chunk.mp3_file.save(filename, File(f), save=False)

        if os.path.exists(file_path):
            os.remove(file_path)

        chunk.word_timestamps = data.get("word_timestamps", [])
        chunk.sentence_indices = data.get("sentence_indices", [])
        chunk.status = "done"
        chunk.save()

    except Exception as e:
        chunk.status = "failed"
        chunk.save()
        raise e


@method_decorator(csrf_exempt, name="dispatch")
class UploadChunkedDocumentView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "Unauthorized"}, status=401)

        document_id = request.data.get("document_id")
        doc, _ = AudioDocument.objects.get_or_create(
            id=document_id,
            defaults={"email": user.email}
        )
        doc.user = user
        doc.email = user.email
        doc.save(update_fields=["user", "email"])

        file = request.FILES.get("file")
        text_content = request.data.get("text")
        upload_image = request.FILES.get("upload_image")

        if file and not upload_image:
            ext = file.name.lower().split(".")[-1]
            if ext in ["jpg", "jpeg", "png", "webp"]:
                upload_image = file
                file = None

        if not file and not text_content and not upload_image:
            return Response({"error": "file, text or image is required"}, status=400)

        try:
            if text_content and not file:
                text = text_content
                doc.file_type = "text"

            elif upload_image:
                doc.upload_image = upload_image
                doc.file_type = "image"
                doc.save()
                text = extract_text_from_image(str(Path(doc.upload_image.path)))

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

            doc.text_content = text
            doc.status = "processing"
            doc.save(update_fields=["text_content", "status"])

            chunks = split_into_chunks(text, CHUNK_SIZE)
            total_chunks = len(chunks)

            # chunk 0 — სინქრონულად
            generate_and_save_chunk(doc, chunks[0], index=0)

            # დანარჩენი — background
            if total_chunks > 1:
                def generate_remaining():
                    for i, chunk_text in enumerate(chunks[1:], start=1):
                        generate_and_save_chunk(doc, chunk_text, index=i)
                    doc.status = "done"
                    doc.save(update_fields=["status"])

                threading.Thread(target=generate_remaining, daemon=True).start()
            else:
                doc.status = "done"
                doc.save(update_fields=["status"])

            first_chunk = AudioDocumentChunk.objects.get(document=doc, index=0)

            return Response({
                "id": str(doc.id),
                "total_chunks": total_chunks,
                "chunk_index": 0,
                "audio_url": request.build_absolute_uri(first_chunk.mp3_file.url),
                "words": first_chunk.word_timestamps,
                "sentence_indices": first_chunk.sentence_indices,
            }, status=201)

        except Exception as e:
            import traceback
            traceback.print_exc()
            doc.status = "failed"
            doc.error_message = str(e)
            doc.save()
            return Response({"error": "processing failed", "detail": str(e)}, status=500)


@api_view(["GET"])
def get_chunk(request, doc_id, chunk_index):
    try:
        doc = AudioDocument.objects.get(id=doc_id)
    except AudioDocument.DoesNotExist:
        return Response({"error": "Document not found"}, status=404)

    try:
        chunk = AudioDocumentChunk.objects.get(document=doc, index=chunk_index)
    except AudioDocumentChunk.DoesNotExist:
        return Response({"error": "Chunk not found", "status": "pending"}, status=404)

    if chunk.status == "pending":
        return Response({"status": "pending"}, status=202)

    if chunk.status == "failed":
        return Response({"error": "Chunk generation failed"}, status=500)

    total_chunks = AudioDocumentChunk.objects.filter(document=doc).count()

    return Response({
        "chunk_index": chunk_index,
        "audio_url": request.build_absolute_uri(chunk.mp3_file.url),
        "words": chunk.word_timestamps,
        "sentence_indices": chunk.sentence_indices,
        "status": "done",
        "total_chunks": total_chunks,
    })