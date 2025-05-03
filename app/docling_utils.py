import shutil
import logging
from pathlib import Path
from PIL import Image
import fitz # PyMuPDF

from docling.document_converter import DocumentConverter, FormatOption, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, PaddleOcrOptions
from docling.datamodel.base_models import InputFormat, ConversionStatus
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling.backend.docling_parse_v4_backend import DoclingParseV4DocumentBackend

# Get logger from config (or create one if run standalone)
try:
    from .config import _log
except ImportError:
    logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)


# --- Docling Setup ---
# Options for general PDF processing (from app2.py)
pdf_pipeline_options_ocr = PdfPipelineOptions()
pdf_pipeline_options_ocr.images_scale = 2.0
pdf_pipeline_options_ocr.generate_page_images = True # Keep if needed, maybe False?
pdf_pipeline_options_ocr.generate_picture_images = True # Keep if needed, maybe False?

# Options for bank statement specific processing (from app.py)
paddle_opts = PaddleOcrOptions(
    lang=["en"],
    use_gpu=False, # Consider making this configurable
    use_angle_cls=True,
    force_full_page_ocr=False
)
pdf_pipeline_opts_bank = PdfPipelineOptions(
    ocr_options=paddle_opts,
    do_ocr=True
)
pdf_format_option_bank = FormatOption(
    pipeline_cls=StandardPdfPipeline,
    pipeline_options=pdf_pipeline_opts_bank,
    backend=DoclingParseV4DocumentBackend
)

# Initialize Docling DocumentConverter for general OCR
# Using PdfFormatOption directly for PDF input
doc_converter_ocr = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_pipeline_options_ocr),
        # Add specific options for DOC/DOCX if default handling isn't sufficient
        # InputFormat.DOC: FormatOption(...),
        # InputFormat.DOCX: FormatOption(...),
    }
)

# Converter specifically for bank statement extraction (using PaddleOCR)
# Using FormatOption as it specifies the pipeline and backend
doc_converter_bank = DocumentConverter(
    format_options={InputFormat.PDF: pdf_format_option_bank}
)
_log.info("Docling converters initialized.")

# --- Helper Functions ---

def get_input_format(file_path: Path) -> InputFormat:
    """Determine the Docling InputFormat based on file extension."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return InputFormat.PDF
    elif ext in [".png", ".jpg", ".jpeg"]:
        # Docling might handle images directly, or we convert first.
        # Let's assume we convert first, so this might not be strictly needed by Docling itself.
        return InputFormat.IMAGE
    elif ext == ".doc":
        return InputFormat.DOC
    elif ext == ".docx":
        return InputFormat.DOCX
    else:
        # Consider returning None or a specific 'Unsupported' enum if defined
        raise ValueError(f"Unsupported file type for Docling processing: {ext}")

async def convert_to_pdf(input_path: Path, output_pdf_path: Path) -> str | None:
    """
    Converts various document types (Image, DOC, DOCX) to PDF.
    Copies if already PDF. Returns the path to the PDF on success, None on failure.
    """
    input_format = get_input_format(input_path) # Re-check format here
    _log.info(f"Attempting conversion of {input_path} (format: {input_format}) to PDF: {output_pdf_path}")

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True) # Ensure output dir exists

    if input_format == InputFormat.PDF:
        try:
            shutil.copy(str(input_path), str(output_pdf_path))
            _log.info(f"Input is already PDF. Copied to {output_pdf_path}")
            return str(output_pdf_path)
        except Exception as e:
            _log.error(f"Failed to copy PDF {input_path} to {output_pdf_path}: {e}")
            return None

    elif input_format == InputFormat.IMAGE:
        try:
            image = Image.open(input_path)
            # Handle transparency and grayscale for PDF saving
            if image.mode == 'RGBA' or image.mode == 'P':
                image = image.convert('RGB')
            elif image.mode == 'L':
                rgb_image = Image.new("RGB", image.size)
                rgb_image.paste(image)
                image = rgb_image

            if image.size[0] > 0 and image.size[1] > 0:
                image.save(output_pdf_path, "PDF", resolution=100.0) # Consider higher resolution?
                _log.info(f"Successfully converted image {input_path} to PDF {output_pdf_path}")
                return str(output_pdf_path)
            else:
                _log.error(f"Image {input_path} is invalid or empty.")
                return None
        except Exception as e:
            _log.error(f"Pillow (PIL) Error converting image {input_path} to PDF: {e}")
            return None

    elif input_format in [InputFormat.DOC, InputFormat.DOCX]:
        # Use Docling itself to convert DOC/DOCX to PDF
        try:
            # Use the general OCR converter instance as it should handle DOC/DOCX
            result = doc_converter_ocr.convert(
                str(input_path),
                output_format=InputFormat.PDF,
                output_path=str(output_pdf_path.parent) # Specify output dir
            )

            # Check result status and locate the output file
            if result.status == ConversionStatus.SUCCESS:
                # Docling might name the output file differently, e.g., original_name.pdf
                # Or it might provide the path in result.output_path
                generated_pdf = None
                if result.output_path and Path(result.output_path).exists():
                    generated_pdf = Path(result.output_path)
                else:
                    # Guess the output name if not provided
                    potential_output = output_pdf_path.parent / f"{input_path.stem}.pdf"
                    if potential_output.exists():
                        generated_pdf = potential_output

                if generated_pdf:
                    # Rename if necessary to match the expected output_pdf_path
                    if generated_pdf != output_pdf_path:
                        shutil.move(str(generated_pdf), str(output_pdf_path))
                    _log.info(f"Successfully converted {input_format.name} {input_path} to PDF {output_pdf_path} using Docling")
                    return str(output_pdf_path)
                else:
                     _log.error(f"Docling conversion from {input_format.name} to PDF succeeded for {input_path}, but output PDF not found.")
                     return None
            else:
                _log.error(f"Docling conversion from {input_format.name} to PDF failed for {input_path}. Status: {result.status}, Error: {result.error}")
                return None
        except Exception as e:
            _log.error(f"Error converting {input_format.name} {input_path} to PDF using Docling: {e}")
            return None
    else:
        _log.warning(f"Conversion to PDF not supported for this format: {input_format}")
        return None


async def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text from a PDF using the general Docling OCR converter."""
    try:
        _log.info(f"Extracting text from PDF: {pdf_path} using general OCR converter")
        result = doc_converter_ocr.convert(pdf_path, raises_on_error=False) # Don't raise, check status
        if result.status in [ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS]:
            extracted_content = result.document.export_to_markdown()
            _log.info(f"Successfully extracted text from {pdf_path}. Length: {len(extracted_content)}")
            return extracted_content
        else:
            _log.error(f"Docling text extraction failed for {pdf_path}. Status: {result.status}, Error: {result.error}")
            return ""
    except Exception as e:
        _log.error(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""

async def extract_bank_statement_data(pdf_path: str) -> str:
    """Extracts text specifically for bank statements using the bank-specific Docling converter."""
    try:
        _log.info(f"Extracting bank statement text from PDF: {pdf_path} using bank statement converter")
        result = doc_converter_bank.convert(pdf_path, raises_on_error=False) # Don't raise, check status
        if result.status in [ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS]:
            extracted_content = result.document.export_to_markdown()
            _log.info(f"Successfully extracted bank statement text from {pdf_path}. Length: {len(extracted_content)}")
            return extracted_content
        else:
            _log.error(f"Docling bank statement extraction failed for {pdf_path}. Status: {result.status}, Error: {result.error}")
            return ""
    except Exception as e:
        _log.error(f"Error extracting bank statement text from PDF {pdf_path}: {e}")
        return ""

def get_pdf_page_count(pdf_path: str) -> int:
    """Gets the number of pages in a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        _log.error(f"Error getting page count for {pdf_path}: {e}")
        return 0 # Return 0 on error
