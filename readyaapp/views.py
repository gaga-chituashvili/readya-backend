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
from .services.google_cts import text_to_mp3
from .services.email import send_email_with_mp3
from rest_framework.decorators import api_view
from django.core.files import File
from django.conf import settings
import os
from .services.services import generate_voice_with_timestamps
from .services.keepz import create_payment
import logging

@method_decorator(csrf_exempt, name="dispatch")
class UploadDocumentView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        file = request.FILES.get("file")
        email = request.data.get("email")
        text_content = request.data.get("text") 
        upload_image = request.FILES.get("upload_image")
        
        # თუ file არის, შევამოწმოთ რა ტიპის ფაილია
        if file and not upload_image:
            file_extension = file.name.lower().split(".")[-1]
            
            # თუ სურათის ფორმატია
            if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                upload_image = file
                file = None
        
        # შემოწმება
        if not file and not text_content and not upload_image:
            return Response({"error": "file, text or image is required"}, status=400)
        
        if not email:
            return Response({"error": "email is required"}, status=400)
        
        # ======= სურათის დამუშავება =======
        if upload_image:
            doc = AudioDocument.objects.create(
                email=email,
                upload_image=upload_image,
                file_type="image",
                status="processing",
            )
            
            try:
                image_path = Path(doc.upload_image.path)
                
                # OCR - ტექსტის ამოღება სურათიდან
                text = extract_text_from_image(str(image_path))
                
                if not text.strip():
                    raise ValueError("No text found in image")
                
                # MP3 გენერაცია
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
        
        # ======= ტექსტის დამუშავება =======
        if text_content and not file:
            doc = AudioDocument.objects.create(
                email=email,
                file_type="text",
                text_content=text_content,
                status="processing",
            )
            
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
        
        # ======= PDF/DOCX დამუშავება =======
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
            status="processing",
        )
        
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

        doc.payment_id = payment_data.get('integratorOrderId')
        doc.save()

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
from django.db import transaction
from .services.payment_service import refund_payment


@csrf_exempt
@api_view(['POST'])
def keepz_webhook(request):

    logger.info(f"🔔 Webhook raw data: {request.data}")

    payload = request.data

    order_id = payload.get('integratorOrderId') or payload.get('orderId')
    status = payload.get('status')
    payment_id = payload.get('paymentId') 

    if not order_id:
        return Response({'error': 'orderId missing'}, status=400)

    try:
        doc = AudioDocument.objects.get(id=order_id)

        if status in ['PAID', 'SUCCESS', 'COMPLETED']:

            try:
                with transaction.atomic():

                    doc.payment_status = 'paid'
                    doc.status = 'processing'
                    doc.save()

                

            except Exception as e:
                logger.error(f"❌ Error after payment, triggering refund: {e}")

                if payment_id:
                    refund_payment(payment_id)

                doc.payment_status = 'refunded'
                doc.status = 'failed'
                doc.save()

                return Response({'refunded': True}, status=200)

            logger.info(f"✅ Payment confirmed for {order_id}")
            return Response({'success': True}, status=200)

        else:
            doc.payment_status = 'failed'
            doc.save()

            logger.warning(f"❌ Payment failed for {order_id}")
            return Response({'success': False}, status=200)

    except AudioDocument.DoesNotExist:
        logger.error(f"Document not found for webhook orderId: {order_id}")
        return Response({'error': 'Document not found'}, status=404)


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