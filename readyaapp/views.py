from annotated_types import doc
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
from django.http import FileResponse, Http404

from .models import AudioDocument
from .services.pdf_reader import extract_text_from_pdf
from .services.docx_reader import extract_text_from_docx
from .services.image_reader import extract_text_from_image
from .services.cartesia_tts import text_to_mp3
from .services.email import send_email_with_mp3
from rest_framework.decorators import api_view
from django.core.files import File
from django.conf import settings
import os
from .services.markupread import generate_voice_with_timestamps
from .services.keepz import create_payment
import logging
from django.db import transaction
import json
from .services.keepz import decrypt_with_aes

@method_decorator(csrf_exempt, name="dispatch")
class UploadDocumentView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file = request.FILES.get("file")
        email = request.data.get("email")
        text_content = request.data.get("text")
        upload_image = request.FILES.get("upload_image")

        if file and not upload_image:
            file_extension = file.name.lower().split(".")[-1]

            if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                upload_image = file
                file = None

        if not file and not text_content and not upload_image:
            return Response({"error": "file, text or image is required"}, status=400)

        if not email:
            return Response({"error": "email is required"}, status=400)

        # IMAGE
        if upload_image:
            doc = AudioDocument.objects.create(
                email=email,
                upload_image=upload_image,
                file_type="image",
                status="pending"
            )

            return Response({
                "document_id": str(doc.id),
                "status": doc.status,
                "file_type": doc.file_type
            }, status=201)

        # TEXT
        if text_content and not file:

            if not text_content.strip():
                return Response({"error": "Text content is empty"}, status=400)

            if len(text_content) > 5000:
                return Response({"error": "Text exceeds 5000 characters limit"}, status=400)

            doc = AudioDocument.objects.create(
                email=email,
                file_type="text",
                text_content=text_content,
                status="pending"
            )

            return Response({
                "document_id": str(doc.id),
                "status": doc.status,
                "file_type": doc.file_type
            }, status=201)

        # PDF / DOCX
        file_extension = file.name.lower().split(".")[-1]

        if file_extension == "pdf":
            file_type = "pdf"
        elif file_extension in ["docx", "doc"]:
            file_type = "docx"
        else:
            return Response(
                {"error": f"Unsupported file type: {file_extension}"},
                status=400
            )

        doc = AudioDocument.objects.create(
            email=email,
            document_file=file,
            file_type=file_type,
            status="pending"
        )

        return Response({
            "document_id": str(doc.id),
            "status": doc.status,
            "file_type": doc.file_type
        }, status=201)
    
    

@api_view(["GET"])
def stream_mp3(request, doc_id):
    try:
        doc = AudioDocument.objects.get(id=doc_id)
        if not doc.mp3_file:
            raise Http404
        return FileResponse(
            open(doc.mp3_file.path, "rb"),
            content_type="audio/mpeg"
        )
    except AudioDocument.DoesNotExist:
        raise Http404
    



@api_view(["POST"])
def generate_voice(request, doc_id):

    try:
        doc = AudioDocument.objects.get(id=doc_id)
    except AudioDocument.DoesNotExist:
        return Response({"error": "Document not found"}, status=404)

    free_used = AudioDocument.objects.filter(email=doc.email).exclude(id=doc.id).exists()

    if free_used and doc.payment_status != "paid":
        return Response({"error": "payment required"}, status=402)

    if doc.file_type == "text":
        text = doc.text_content

    elif doc.file_type == "pdf":
        text = extract_text_from_pdf(doc.document_file.path)

    elif doc.file_type == "docx":
        text = extract_text_from_docx(doc.document_file.path)

    elif doc.file_type == "image":
        text = extract_text_from_image(doc.upload_image.path)

    else:
        return Response({"error": "Unsupported file type"}, status=400)

    if not text or not text.strip():
        return Response({"error": "Empty text extracted"}, status=400)

    if doc.mp3_file:
        old_path = doc.mp3_file.path
        doc.mp3_file.delete(save=False)

        if os.path.exists(old_path):
            os.remove(old_path)

    data = generate_voice_with_timestamps(text)

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
        "stream_url": request.build_absolute_uri(f"/stream/{doc.id}/"),
        "words": doc.word_timestamps
    })




logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(['POST'])
def create_payment_view(request):

    email = request.data.get('email')

    if not email:
        return Response({'error': 'Email is required'}, status=400)

    doc = AudioDocument.objects.create(
        email=email,
        status='pending_payment',
        payment_status='pending',
        payment_amount=0.1,
    )

    try:
        payment_data = create_payment(
            amount=0.1,
            email=email,
            order_id=str(doc.id),
            description="Readya Audio Generation"
        )

        logger.info(f"🔓 Decrypted Keepz response: {payment_data}")


        return Response({
            'document_id': str(doc.id),
            'payment_url': payment_data.get('urlForQR'),
            'order_id': payment_data.get('integratorOrderId'),
        }, status=201)

    except Exception as e:
        logger.error(f"Payment creation error: {str(e)}")

        doc.payment_status = 'failed'
        doc.save()

        return Response({
            'error': 'Payment creation failed',
            'detail': str(e)
        }, status=500)

# ===============================
# STEP 2 — KEEPZ WEBHOOK
# ===============================

logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(["POST"])
def keepz_webhook(request):

    logger.info(f"🔔 RAW Keepz webhook payload: {request.data}")

    payload = request.data


    if payload.get("encryptedData"):

        try:
            decrypted_json = decrypt_with_aes(
                payload["encryptedKeys"],
                payload["encryptedData"],
                settings.KEEPZ_PRIVATE_KEY,
            )

            payload = json.loads(decrypted_json)

            logger.info(f"🔓 Decrypted webhook payload: {payload}")

        except Exception as e:
            logger.error(f"❌ Webhook decrypt failed: {str(e)}")
            return Response({"error": "decrypt failed"}, status=400)

   
    order_id = payload.get("integratorOrderId") or payload.get("orderId")
    status = (payload.get("status") or "").upper()
    amount = payload.get("amount") or payload.get("acquiringAmount")

    if not order_id:
        logger.error("❌ orderId missing in webhook")
        return Response({"error": "orderId missing"}, status=400)

   
    try:
        doc = AudioDocument.objects.get(id=order_id)

    except AudioDocument.DoesNotExist:
        logger.error(f"❌ Document not found for orderId: {order_id}")
        return Response({"error": "Document not found"}, status=404)


    if doc.payment_status == "paid":
        logger.info(f"⚠️ Webhook already processed for {order_id}")
        return Response({"already_processed": True}, status=200)

 
    if status == "SUCCESS":

        try:
            with transaction.atomic():

                doc.payment_status = "paid"
                doc.status = "processing"

                if amount:
                    doc.payment_amount = amount

                doc.save()

            logger.info(f"✅ Payment confirmed for document {order_id}")

            return Response({"success": True}, status=200)

        except Exception as e:
            logger.error(f"❌ DB update failed: {str(e)}")
            return Response({"error": "database error"}, status=500)

    
    else:

        doc.payment_status = "failed"
        doc.status = "failed"
        doc.save()

        logger.warning(f"❌ Payment failed for document {order_id}")

        return Response({"success": False}, status=200)

# ===============================
# STEP 3 — CHECK PAYMENT STATUS
# ===============================
@api_view(['GET'])
def check_payment_status(request, document_id):

    try:
        doc = AudioDocument.objects.get(id=document_id)
        return Response({
            'document_id': str(doc.id),
            'payment_status': doc.payment_status,
            'status': doc.status,
            'can_upload': doc.payment_status == 'paid',
        }, status=200)

    except AudioDocument.DoesNotExist:
        return Response({'error': 'Document not found'}, status=404)