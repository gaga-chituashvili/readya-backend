from readyaapp.services.openai_chat import chat_with_document
from rest_framework.decorators import api_view, authentication_classes,permission_classes
from readyaapp.services.openai_chat import chat_with_document
from rest_framework.response import Response
from rest_framework.response import Response
from ..models import AudioDocument
from readyaapp.services.pdf_reader import extract_text_from_pdf
from readyaapp.services.docx_reader import extract_text_from_docx
from readyaapp.services.image_reader import extract_text_from_image
from readyaapp.services.openai_chat import chat_with_document
from rest_framework.decorators import api_view
from readyaapp.services.openai_chat import chat_with_document
from rest_framework.permissions import AllowAny



@api_view(['POST'])
@authentication_classes([])       
@permission_classes([AllowAny])   
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
    

