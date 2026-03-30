import threading
from pathlib import Path
from uuid import uuid4
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.decorators import method_decorator
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from readyaapp.services.cartesia_tts import text_to_mp3
from readyaapp.services.email import send_email_with_mp3
from ..models import AudioDocument
from readyaapp.services.pdf_reader import extract_text_from_pdf
from readyaapp.services.docx_reader import extract_text_from_docx
from readyaapp.services.image_reader import extract_text_from_image
from django.conf import settings



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

        email = request.data.get("email")

        if not email:
            return Response({"error": "email is required"}, status=400)

        free_usage = AudioDocument.objects.filter(
            email=email,
            mp3_file__isnull=False
        ).exclude(id=payment_doc.id).exists()

        if free_usage and payment_doc.payment_status != "paid":
            return Response({"error": "payment required"}, status=402)


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
        

        doc = payment_doc
        doc.email = email
        doc.save(update_fields=["email"])


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
                mp3_dir = Path(settings.MEDIA_ROOT) / "uploads/mp3"
                mp3_dir.mkdir(parents=True, exist_ok=True)
                mp3_path = mp3_dir / mp3_filename
                
                text_to_mp3(text, str(mp3_path))
                
                doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
                doc.text_content = text
                doc.status = "done"
                doc.save()

                threading.Thread(
                target=send_email_with_mp3,
                args=(email, str(mp3_path)),
                daemon=True
                ).start()
                
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
                mp3_dir = Path(settings.MEDIA_ROOT) / "uploads/mp3"
                mp3_dir.mkdir(parents=True, exist_ok=True)
                mp3_path = mp3_dir / mp3_filename
                
                text_to_mp3(text_content, str(mp3_path))
                
                doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
                doc.status = "done"
                doc.save()

                try:
                    threading.Thread(
                        target=send_email_with_mp3,
                        args=(email, str(mp3_path)),
                        daemon=True
                    ).start()

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
            mp3_path = Path(settings.MEDIA_ROOT) / "uploads/mp3" / mp3_filename
            mp3_path.parent.mkdir(parents=True, exist_ok=True)
            
            text_to_mp3(text, str(mp3_path))
            
            doc.mp3_file.name = f"uploads/mp3/{mp3_filename}"
            doc.status = "done"
            doc.save()

            threading.Thread(
                target=send_email_with_mp3,
                args=(email, str(mp3_path)),
                daemon=True
            ).start()

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


