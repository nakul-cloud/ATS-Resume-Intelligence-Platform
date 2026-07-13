from io import BytesIO
import pdfplumber
from app.utils.logger import logger

def extract_pdf_text(pdf_bytes: bytes, max_chars: int = 10000) -> str:
    """
    Extracts plain text from raw PDF bytes.
    Raises ValueError if the PDF is corrupt or cannot be parsed.
    """
    if not pdf_bytes:
        raise ValueError("PDF bytes cannot be empty")
        
    try:
        text_chunks = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_chunks.append(text)
                    
        extracted_text = "\n".join(text_chunks).strip()
        
        if not extracted_text:
            raise ValueError("No text could be extracted from the PDF (it might be scanned or empty)")
            
        # Remove null bytes to prevent CharacterNotInRepertoireError in PostgreSQL
        sanitized_text = extracted_text.replace("\x00", "")
        return sanitized_text[:max_chars]
    except Exception as e:
        try:
            decoded = pdf_bytes.decode('utf-8', errors='ignore').strip()
            if decoded and len(decoded) > 10:
                logger.info("PDF parsing failed; successfully fell back to UTF-8 decoding raw bytes.")
                # Remove null bytes to prevent CharacterNotInRepertoireError in PostgreSQL
                sanitized_decoded = decoded.replace("\x00", "")
                return sanitized_decoded[:max_chars]
        except Exception:
            pass
        logger.error(f"Failed to extract text from PDF: {e}")
        raise ValueError(f"Failed to parse PDF file: {e}") from e

