import io
from typing import Optional
from pdfminer.high_level import extract_text
from pdfminer.pdfparser import PDFSyntaxError
import PyPDF2
from fastapi import UploadFile


class PDFExtractor:
    """Service for extracting text from PDF files."""

    async def extract(self, file: UploadFile) -> str:
        """
        Extract text from uploaded PDF file.
        Uses PDFMiner as primary, PyPDF2 as fallback.
        """
        content = await file.read()

        # Try PDFMiner first (better text extraction)
        text = self._extract_with_pdfminer(content)

        # Fallback to PyPDF2 if PDFMiner fails
        if not text or len(text.strip()) < 50:
            text = self._extract_with_pypdf2(content)

        if not text or len(text.strip()) < 10:
            raise ValueError("Could not extract text from PDF. File may be scanned/image-based.")

        return text

    def _extract_with_pdfminer(self, content: bytes) -> Optional[str]:
        """Extract text using PDFMiner."""
        try:
            pdf_file = io.BytesIO(content)
            text = extract_text(pdf_file)
            return text
        except (PDFSyntaxError, Exception) as e:
            print(f"PDFMiner extraction failed: {e}")
            return None

    def _extract_with_pypdf2(self, content: bytes) -> Optional[str]:
        """Extract text using PyPDF2 as fallback."""
        try:
            pdf_file = io.BytesIO(content)
            reader = PyPDF2.PdfReader(pdf_file)

            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            return "\n".join(text_parts)
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
            return None

    def get_pdf_info(self, content: bytes) -> dict:
        """Get PDF metadata."""
        try:
            pdf_file = io.BytesIO(content)
            reader = PyPDF2.PdfReader(pdf_file)

            info = reader.metadata
            return {
                "pages": len(reader.pages),
                "title": info.title if info else None,
                "author": info.author if info else None,
            }
        except Exception:
            return {"pages": 0, "title": None, "author": None}
