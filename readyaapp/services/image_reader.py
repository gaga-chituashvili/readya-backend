from PIL import Image
import pytesseract

def extract_text_from_image(path: str) -> str:
    """Extract text from image using OCR"""
    try:
        image = Image.open(path)
        
        text = pytesseract.image_to_string(image, lang='kat')
        
        if not text.strip():
            raise ValueError("No text found in image")
        
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to extract text from image: {str(e)}")