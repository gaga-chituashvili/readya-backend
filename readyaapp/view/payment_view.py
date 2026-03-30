from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from ..models import AudioDocument
from readyaapp.services.pdf_reader import extract_text_from_pdf
from readyaapp.services.docx_reader import extract_text_from_docx
from readyaapp.services.image_reader import extract_text_from_image
from readyaapp.services.openai_chat import chat_with_document
from readyaapp.services.keepz import create_payment, decrypt_with_aes
from rest_framework.decorators import api_view
from django.conf import settings
from readyaapp.services.openai_chat import chat_with_document
from readyaapp.services.keepz import create_payment
import logging
from django.db import transaction
import json
from readyaapp.services.keepz_crypto import decrypt_with_aes
from readyaapp.services.openai_chat import chat_with_document


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
    





@api_view(['POST'])
def chat_ai(request, doc_id=None):
    try:
        user_message = request.data.get('message')
        conversation_history = request.data.get('history', [])

        if not user_message:
            return Response({'error': 'message is required'}, status=400)

        document_text = None

        if doc_id:
            try:
                doc = AudioDocument.objects.get(id=doc_id)

                if doc.file_type == "pdf":
                    if not doc.document_file:
                        return Response({'error': 'PDF file missing'}, status=400)
                    document_text = extract_text_from_pdf(doc.document_file.path)

                elif doc.file_type == "docx":
                    if not doc.document_file:
                        return Response({'error': 'DOCX file missing'}, status=400)
                    document_text = extract_text_from_docx(doc.document_file.path)

                elif doc.file_type == "image":
                    document_text = extract_text_from_image(doc.upload_image.path)

                elif doc.file_type == "text":
                    document_text = doc.text_content

                else:
                    return Response({'error': 'Unsupported file type'}, status=400)

                if not document_text or not document_text.strip():
                    return Response({'error': 'No text found in document'}, status=400)

            except AudioDocument.DoesNotExist:
                return Response({'error': 'Document not found'}, status=404)

        ai_response = chat_with_document(
            user_message=user_message,
            document_text=document_text,
            conversation_history=conversation_history
        )

        return Response({
            "response": ai_response,
            "message": user_message
        }, status=200)

    except Exception as e:
        print(f"❌ Chat Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)
    

