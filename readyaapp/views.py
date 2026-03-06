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

        document_id = request.data.get("document_id")

        if not document_id:
            return Response({"error": "document_id is required"}, status=400)

        try:
            payment_doc = AudioDocument.objects.get(id=document_id)
        except AudioDocument.DoesNotExist:
            return Response({"error": "Document not found"}, status=404)

        if payment_doc.payment_status != "paid":
            return Response({"error": "payment required"}, status=402)


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
        

        doc = payment_doc
        doc.email = email


        # ======= IMAGE =======
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
                mp3_dir = Path("media/uploads/mp3")
                mp3_dir.mkdir(parents=True, exist_ok=True)
                mp3_path = mp3_dir / mp3_filename
                
                text_to_mp3(text, str(mp3_path))
                
                doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
                doc.text_content = text
                doc.status = "done"
                doc.save()

                send_email_with_mp3(email, str(mp3_path))
                
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
                    "file_type": doc.file_type,
                    "mp3_url": doc.mp3_file.url,
                    "extracted_text": text[:200] + "..." if len(text) > 200 else text,
                },
                status=201,
            )
        

        # ======= TEXT =======
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
                mp3_dir = Path("media/uploads/mp3")
                mp3_dir.mkdir(parents=True, exist_ok=True)
                mp3_path = mp3_dir / mp3_filename
                
                text_to_mp3(text_content, str(mp3_path))
                
                doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
                doc.status = "done"
                doc.save()

                try:
                    send_email_with_mp3(email, str(mp3_path))
                except Exception as e:
                    print("Email sending failed:", e)

                
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
                    "file_type": doc.file_type,
                    "mp3_url": doc.mp3_file.url,
                },
                status=201,
            )
        

        # ======= PDF / DOCX =======
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
                raise ValueError(f"No extractable text found in {file_type.upper()}")
            
            mp3_filename = f"{uuid4()}.mp3"
            mp3_path = doc_path.parent.parent / "mp3" / mp3_filename
            mp3_path.parent.mkdir(parents=True, exist_ok=True)
            
            text_to_mp3(text, str(mp3_path))
            
            doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
            doc.status = "done"
            doc.save()

            send_email_with_mp3(email, str(mp3_path))

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
                "file_type": doc.file_type,
                "mp3_url": doc.mp3_file.url,
            },
            status=201,
        )

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

    # ===== PAYMENT CHECK =====
    if doc.payment_status != "paid":
        return Response(
            {"error": "payment required"},
            status=402
        )

    # ===== FILE CHECK =====
    if not doc.file_type:
        return Response(
            {"error": "No uploaded file or text found"},
            status=400
        )

    # ===== TEXT EXTRACTION =====
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

    # ===== EMPTY TEXT CHECK =====
    if not text or not text.strip():
        return Response({"error": "Empty text extracted"}, status=400)

    # ===== DELETE OLD MP3 =====
    if doc.mp3_file:
        old_path = doc.mp3_file.path
        doc.mp3_file.delete(save=False)
        if os.path.exists(old_path):
            os.remove(old_path)

    # ===== GENERATE VOICE =====
    data = generate_voice_with_timestamps(text)

    if not data or "audio_url" not in data:
        return Response({"error": "Voice generation failed"}, status=500)

    filename = data["audio_url"].split("/")[-1]
    temp_path = os.path.join(settings.MEDIA_ROOT, filename)

    if not os.path.exists(temp_path):
        return Response({"error": "Generated file missing"}, status=500)

    # ===== SAVE MP3 =====
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