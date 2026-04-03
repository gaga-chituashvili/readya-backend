
import os
from django.core.files import File
from requests import request
from rest_framework.response import Response
from readyaapp.services.markupread import generate_voice_with_timestamps
from readyaapp.models import AudioDocument
from readyaapp.services.pdf_reader import extract_text_from_pdf
from readyaapp.services.docx_reader import extract_text_from_docx
from readyaapp.services.image_reader import extract_text_from_image

from rest_framework.decorators import api_view
from django.conf import settings


@api_view(["POST"])
def generate_voice(request, doc_id):

    speed = float(request.data.get("speed", 0.92))
    voice_id = request.data.get("voice_id")

    try:
        doc = AudioDocument.objects.get(id=doc_id)
    except AudioDocument.DoesNotExist:
        return Response({"error": "Document not found"}, status=404)
    
    if doc.mp3_file:
        return Response({
            "stream_url": f"/stream/{doc.id}/",
            "words": doc.word_timestamps
        })

    email = doc.email

    free_usage = AudioDocument.objects.filter(
        email=email,
        mp3_file__isnull=False
    ).exclude(id=doc.id).exists()

    if free_usage and doc.payment_status != "paid":
        return Response(
            {"error": "payment required"},
            status=402
        )

    
    if not doc.file_type:
        return Response(
            {"error": "No uploaded file or text found"},
            status=400
        )

   
    if doc.file_type == "text":
        text = doc.text_content

    elif doc.file_type == "pdf":
        if not doc.document_file:
            return Response({"error": "PDF file missing"}, status=400)
        text = extract_text_from_pdf(doc.document_file.path)

    elif doc.file_type == "docx":
        if not doc.document_file:
            return Response({"error": "DOCX file missing"}, status=400)
        text = extract_text_from_docx(doc.document_file.path)

    elif doc.file_type == "image":
        if not doc.upload_image:
            return Response({"error": "Image file missing"}, status=400)
        text = extract_text_from_image(doc.upload_image.path)

    else:
        return Response({"error": "Unsupported file type"}, status=400)

   
    if not text.strip():
        return Response({"error": "Empty text extracted"}, status=400)


    data = generate_voice_with_timestamps(text, speed=speed, voice_id=voice_id)
    

    if not data or "audio_url" not in data:
        return Response({"error": "Voice generation failed"}, status=500)

    filename = data["audio_url"].split("/")[-1]
    temp_path = os.path.join(settings.MEDIA_ROOT, filename)

    if not os.path.exists(temp_path):
        return Response({"error": "Generated file missing"}, status=500)

    
    with open(temp_path, "rb") as f:
        doc.mp3_file.save(filename, File(f), save=False)

    doc.word_timestamps = data.get("words", [])
    doc.status = "done"
    doc.save()

    os.remove(temp_path)

    return Response({
        "stream_url": f"/stream/{doc.id}/",
        "words": doc.word_timestamps
    })




