from PyPDF2 import PdfReader

def extract_text_from_pdf(path: str) -> str:
    text_parts = []

    with open(path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    text = "\n".join(text_parts).strip()
    if not text:
        raise ValueError("PDF has no extractable text")

    return text
