from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from readyaapp.models import AudioDocument, SubscriptionPlan
from django.contrib.auth import get_user_model
from readyaapp.services.keepz import create_payment
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import logging
from django.db import transaction
import json
from readyaapp.services.keepz_crypto import decrypt_with_aes
from django.utils import timezone
from datetime import timedelta

User = get_user_model()
logger = logging.getLogger(__name__)


# ===============================
# STEP 1 — CREATE PAYMENT
# ===============================


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
def create_payment_view(request):

    user = request.user 
    email = user.email

    plan_id = request.data.get('plan_id')

    if not plan_id:
        return Response({'error': 'plan_id required'}, status=400)

    try:
        plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=404)

    doc = AudioDocument.objects.create(
        email=email,
        status='pending_payment',
        payment_status='pending',
        payment_amount=plan.price,
        plan=plan
    )

    payment_data = create_payment(
        amount=str(plan.price), 
        email=email, 
        order_id=str(doc.id),
        description=f"{plan.name} subscription"
    )

    return Response({
        'document_id': str(doc.id),
        'payment_url': payment_data.get('urlForQR'),
        'order_id': payment_data.get('integratorOrderId'),
    }, status=201)

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

                

                try:
                    user = User.objects.get(email=doc.email)
                    plan = doc.plan

                    if not plan:
                        logger.error("❌ Plan missing on document")
                        return Response({"error": "plan missing"}, status=400)

                   
                    user.subscription_plan = plan

                    if user.subscription_end and user.subscription_end > timezone.now():
                        user.subscription_end += timedelta(days=plan.duration_days)
                    else:
                        user.subscription_end = timezone.now() + timedelta(days=plan.duration_days)

                    user.save(update_fields=["subscription_plan", "subscription_end"])

                    logger.info(f"🎉 Subscription activated for {user.email}")

                except User.DoesNotExist:
                    logger.warning(f"⚠️ User not found for email {doc.email}")

                doc.save(update_fields=["payment_status", "status", "payment_amount"])

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