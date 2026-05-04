"""
PDF conversion utilities for document handling.
Converts images (.jpg, .png) and Word documents (.docx) to PDF format.
Designed for safe production deployment on Linux servers.
"""

import os
import logging
from pathlib import Path
from io import BytesIO

from PIL import Image
from docx import Document as DocxDocument
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class PDFConversionError(Exception):
    """Raised when PDF conversion fails."""
    pass


class ImageToPDFConverter:
    """Convert image files (JPG, PNG) to PDF using Pillow."""
    
    SUPPORTED_FORMATS = {'image/jpeg', 'image/png', 'image/jpg', 'image/webp'}
    MAX_IMAGE_SIZE = (2400, 3200)  # Prevent massive PDFs
    
    @staticmethod
    def convert(file_content, original_filename):
        """
        Convert image to PDF.
        
        Args:
            file_content: File bytes or file-like object
            original_filename: Original image filename
            
        Returns:
            tuple: (pdf_bytes, pdf_filename)
            
        Raises:
            PDFConversionError: If conversion fails
        """
        try:
            # Open image
            if isinstance(file_content, bytes):
                image = Image.open(BytesIO(file_content))
            else:
                file_content.seek(0)
                image = Image.open(file_content)
            
            # Validate image
            if image.size[0] > ImageToPDFConverter.MAX_IMAGE_SIZE[0] or \
               image.size[1] > ImageToPDFConverter.MAX_IMAGE_SIZE[1]:
                raise PDFConversionError("Image dimensions exceed maximum allowed size")
            
            # Convert RGBA/transparency to RGB (PDF doesn't support transparency well)
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Create PDF
            pdf_buffer = BytesIO()
            image.save(pdf_buffer, format='PDF', quality=95)
            pdf_buffer.seek(0)
            
            # Generate PDF filename
            base_name = Path(original_filename).stem
            pdf_filename = f"{base_name}_converted.pdf"
            
            logger.info(f"✓ Image converted to PDF: {original_filename} → {pdf_filename}")
            return pdf_buffer.getvalue(), pdf_filename
            
        except Exception as e:
            error_msg = f"Image to PDF conversion failed: {str(e)}"
            logger.error(error_msg)
            raise PDFConversionError(error_msg) from e


class DocxToPDFConverter:
    """Convert Word documents (.docx) to PDF using python-docx + reportlab."""
    
    SUPPORTED_FORMATS = {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
    MAX_PAGES = 500  # Prevent infinite loops
    
    @staticmethod
    def convert(file_content, original_filename):
        """
        Convert DOCX to PDF by extracting text and re-rendering with ReportLab.
        This is a best-effort conversion that preserves text content.
        
        Args:
            file_content: File bytes or file-like object
            original_filename: Original DOCX filename
            
        Returns:
            tuple: (pdf_bytes, pdf_filename)
            
        Raises:
            PDFConversionError: If conversion fails
        """
        try:
            # Parse DOCX
            if isinstance(file_content, bytes):
                docx_file = BytesIO(file_content)
            else:
                file_content.seek(0)
                docx_file = file_content
            
            doc = DocxDocument(docx_file)
            
            # Create PDF
            pdf_buffer = BytesIO()
            page_size = A4
            width, height = page_size
            margin = 0.5 * inch
            
            c = canvas.Canvas(pdf_buffer, pagesize=page_size)
            c.setFont("Helvetica", 10)
            
            y_position = height - margin
            line_height = 14
            page_count = 0
            
            # Extract and render text
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    y_position -= line_height / 2
                    continue
                
                # Wrap long lines
                max_chars = 100
                if len(text) > max_chars:
                    for i in range(0, len(text), max_chars):
                        chunk = text[i:i+max_chars]
                        if y_position < margin:
                            page_count += 1
                            if page_count > DocxToPDFConverter.MAX_PAGES:
                                raise PDFConversionError(f"Document exceeds {DocxToPDFConverter.MAX_PAGES} pages")
                            c.showPage()
                            y_position = height - margin
                            c.setFont("Helvetica", 10)
                        c.drawString(margin, y_position, chunk)
                        y_position -= line_height
                else:
                    if y_position < margin:
                        page_count += 1
                        if page_count > DocxToPDFConverter.MAX_PAGES:
                            raise PDFConversionError(f"Document exceeds {DocxToPDFConverter.MAX_PAGES} pages")
                        c.showPage()
                        y_position = height - margin
                        c.setFont("Helvetica", 10)
                    c.drawString(margin, y_position, text)
                    y_position -= line_height
            
            c.save()
            pdf_buffer.seek(0)
            
            # Generate PDF filename
            base_name = Path(original_filename).stem
            pdf_filename = f"{base_name}_converted.pdf"
            
            logger.info(f"✓ DOCX converted to PDF: {original_filename} → {pdf_filename}")
            return pdf_buffer.getvalue(), pdf_filename
            
        except Exception as e:
            error_msg = f"DOCX to PDF conversion failed: {str(e)}"
            logger.error(error_msg)
            raise PDFConversionError(error_msg) from e


def convert_document_to_pdf(file_obj, content_type, original_filename):
    """
    Route document conversion based on MIME type.
    
    Args:
        file_obj: File bytes or file-like object
        content_type: MIME type
        original_filename: Original filename
        
    Returns:
        tuple: (pdf_bytes, pdf_filename) or (None, None) if conversion skipped
        
    Raises:
        PDFConversionError: If conversion fails
    """
    try:
        if content_type in ImageToPDFConverter.SUPPORTED_FORMATS:
            return ImageToPDFConverter.convert(file_obj, original_filename)
        elif content_type in DocxToPDFConverter.SUPPORTED_FORMATS:
            return DocxToPDFConverter.convert(file_obj, original_filename)
        else:
            logger.warning(f"No converter available for MIME type: {content_type}")
            return None, None
    except PDFConversionError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during PDF conversion: {str(e)}")
        raise PDFConversionError(f"Unexpected conversion error: {str(e)}") from e
