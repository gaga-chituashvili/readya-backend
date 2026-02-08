from docx import Document

def extract_text_from_docx(path: str) -> str:
    """Extract text from Word document"""
    doc = Document(path)
    text_parts = []
    
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)
    
    text = "\n".join(text_parts).strip()
    
    if not text:
        raise ValueError("DOCX has no extractable text")
    
    return text