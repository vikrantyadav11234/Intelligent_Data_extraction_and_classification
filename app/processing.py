import asyncio
import json
import tempfile
import logging
from pathlib import Path
from tqdm.auto import tqdm
import os # For unlink

# Import utilities from other modules in the package
try:
    from .config import _log, SUPPORTED_EXTENSIONS
    from .docling_utils import (
        convert_to_pdf,
        get_pdf_page_count,
        extract_text_from_pdf,
        extract_bank_statement_data,
        get_input_format # Needed for initial filtering
    )
    from .gemini_utils import (
        classify_and_extract_with_gemini,
        extract_full_bank_statement_with_gemini
    )
    # Import schemas if validation is done here
    # from .schemas import BANK_STATEMENT_SCHEMA, SIMPLE_TEXT_SCHEMA
except ImportError:
    # Fallback for potential standalone testing (less likely needed here)
    logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.pdf', '.doc', '.docx']
    # Define dummy functions or raise errors if run standalone without dependencies
    async def convert_to_pdf(*args, **kwargs): raise NotImplementedError
    def get_pdf_page_count(*args, **kwargs): raise NotImplementedError
    async def extract_text_from_pdf(*args, **kwargs): raise NotImplementedError
    async def extract_bank_statement_data(*args, **kwargs): raise NotImplementedError
    def get_input_format(*args, **kwargs): raise NotImplementedError
    async def classify_and_extract_with_gemini(*args, **kwargs): raise NotImplementedError
    async def extract_full_bank_statement_with_gemini(*args, **kwargs): raise NotImplementedError


async def process_single_document(input_file_path: Path, base_input_folder: Path, output_folder: Path, temp_dir: Path):
    """
    Processes a single document: converts to PDF, extracts text, classifies,
    extracts data using Gemini, and saves the final JSON output.

    Args:
        input_file_path: Absolute path to the input file.
        base_input_folder: Absolute path to the root input folder (for relative path calculation).
        output_folder: Absolute path to the root output folder.
        temp_dir: Absolute path to the temporary directory for intermediate files.
    """
    _log.info(f"Starting processing for: {input_file_path.name}")
    # Calculate relative path for output structure preservation
    try:
        relative_path = input_file_path.relative_to(base_input_folder)
    except ValueError:
        _log.error(f"Could not determine relative path for {input_file_path} based on {base_input_folder}. Skipping.")
        # Fallback: save directly in output_folder? Or skip? Skipping is safer.
        relative_path = input_file_path.name # Fallback to just the filename

    output_subfolder = output_folder / relative_path.parent
    output_subfolder.mkdir(parents=True, exist_ok=True)
    output_json_path = output_subfolder / f"{input_file_path.stem}.json"
    # Create a unique temp PDF name within the shared temp_dir
    temp_pdf_path = temp_dir / f"{input_file_path.stem}_{os.urandom(4).hex()}.pdf"

    try:
        # 1. Convert to PDF (handles images, doc, docx, pdf copy)
        # This function now returns None on failure
        converted_pdf_path_str = await convert_to_pdf(input_file_path, temp_pdf_path)

        if not converted_pdf_path_str:
            _log.error(f"Conversion to PDF failed for {input_file_path}. Skipping file.")
            return # Skip processing this file

        converted_pdf_path = Path(converted_pdf_path_str)
        if not converted_pdf_path.exists():
             _log.error(f"Converted PDF path {converted_pdf_path} does not exist. Skipping file.")
             return # Skip processing this file


        # 2. Get Page Count
        page_count = get_pdf_page_count(str(converted_pdf_path))
        is_multi_page = page_count > 1
        _log.info(f"Document '{input_file_path.name}' has {page_count} page(s).")

        # 3. Extract Text (using general OCR first)
        extracted_text = await extract_text_from_pdf(str(converted_pdf_path))
        if not extracted_text or not extracted_text.strip():
            _log.warning(f"No text extracted from {converted_pdf_path}. Skipping Gemini and saving empty/placeholder JSON.")
            # Decide what to save: empty JSON, simple text with empty string, or skip?
            # Saving simple text structure with empty text for consistency.
            final_json_output = {
                "file_name": input_file_path.name,
                "extracted_text": ""
            }
            with open(output_json_path, 'w', encoding='utf-8') as json_file:
                json.dump(final_json_output, json_file, indent=4)
            _log.info(f"Saved placeholder JSON for {input_file_path.name} due to no extracted text.")
            return # Stop processing this file further

        # 4. Classify and Extract with Gemini (using potentially truncated text)
        doc_type, initial_extracted_data = await classify_and_extract_with_gemini(extracted_text, is_multi_page)

        # 5. Prepare Final JSON Output based on classification
        final_json_output = {}
        if doc_type == "bank_statement":
            _log.info(f"Document '{input_file_path.name}' classified as BANK STATEMENT.")
            # If bank statement, potentially re-extract full text and call Gemini again
            if is_multi_page:
                _log.info(f"Attempting full text extraction for multi-page bank statement: {converted_pdf_path}")
                # Use the bank-specific extractor for potentially better results on full doc
                full_bank_text = await extract_bank_statement_data(str(converted_pdf_path))
                if full_bank_text and full_bank_text.strip():
                    # Call Gemini again for full extraction
                    final_json_output = await extract_full_bank_statement_with_gemini(full_bank_text)
                    if not final_json_output: # Check if extraction failed
                         _log.warning(f"Full bank statement extraction failed for {input_file_path.name}. Falling back to initial Gemini data.")
                         final_json_output = initial_extracted_data # Fallback
                else:
                    _log.warning(f"Failed to extract full bank statement text using bank converter for {input_file_path.name}. Falling back to initial Gemini data.")
                    final_json_output = initial_extracted_data # Fallback
            else:
                # Single page bank statement - use the data already extracted by classify_and_extract
                final_json_output = initial_extracted_data

            # Ensure final output is not empty if it was supposed to be a bank statement
            if not final_json_output:
                 _log.warning(f"Final JSON for bank statement '{input_file_path.name}' is empty. Saving initial classification data as fallback.")
                 final_json_output = initial_extracted_data # Fallback to whatever classify returned

        elif doc_type == "simple_text":
            _log.info(f"Document '{input_file_path.name}' classified as SIMPLE TEXT.")
            # Use the full extracted text from step 3
            final_json_output = {
                "file_name": input_file_path.name,
                "extracted_text": extracted_text # Use the full text
            }
            # We can use the 'extracted_data' from classify_and_extract if we trust Gemini's simple text output format
            # final_json_output = initial_extracted_data
            # Add filename if missing from Gemini's simple text output
            # if "file_name" not in final_json_output:
            #     final_json_output["file_name"] = input_file_path.name


        # 6. Save Final Output JSON
        if final_json_output: # Ensure we have something to save
            with open(output_json_path, 'w', encoding='utf-8') as json_file:
                json.dump(final_json_output, json_file, indent=4)
            _log.info(f"Successfully processed and saved output for '{input_file_path.name}' to {output_json_path}")
        else:
            _log.warning(f"No final JSON data generated for '{input_file_path.name}'. Skipping save.")


    except Exception as e:
        _log.error(f"Unhandled error processing document {input_file_path}: {e}", exc_info=True) # Log traceback
    finally:
        # 7. Clean up intermediate PDF file from the central temp directory
        if temp_pdf_path.exists():
            try:
                temp_pdf_path.unlink()
                _log.debug(f"Deleted intermediate file: {temp_pdf_path}")
            except OSError as e:
                # Log warning but continue, temp dir will be cleaned eventually
                _log.warning(f"Could not delete intermediate file {temp_pdf_path}: {e}")


async def process_folder_recursive(input_folder_str: str, output_folder_str: str):
    """
    Processes all supported documents in a folder recursively.
    Manages temporary directory creation and cleanup.
    """
    input_folder = Path(input_folder_str).resolve() # Use absolute paths
    output_folder = Path(output_folder_str).resolve()

    if not input_folder.is_dir():
        _log.error(f"Input path is not a valid directory: {input_folder}")
        raise ValueError(f"Input folder does not exist or is not a directory: {input_folder}")

    output_folder.mkdir(parents=True, exist_ok=True) # Ensure output folder exists

    # Create a single temporary directory for all intermediate files for this run
    with tempfile.TemporaryDirectory(prefix="ocr_app_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        _log.info(f"Using temporary directory for intermediate files: {temp_dir}")

        tasks = []
        file_count = 0
        # Collect all files matching supported extensions first
        for file_path in input_folder.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                file_count += 1
                # Create task: pass absolute paths
                tasks.append(process_single_document(
                    file_path.resolve(),
                    input_folder, # Pass base input folder for relative path calculation
                    output_folder,
                    temp_dir
                ))
            elif file_path.is_file():
                 _log.info(f"Skipping unsupported file type: {file_path.name}")


        _log.info(f"Found {file_count} supported files to process.")
        if not tasks:
            _log.warning("No supported files found in the input folder.")
            return # Exit early if no files

        # Run tasks concurrently with progress bar
        results = []
        # Use asyncio.gather for potentially better performance than as_completed for many tasks
        # results = await asyncio.gather(*tasks, return_exceptions=True) # return_exceptions=True logs errors but continues

        # Or stick with as_completed for progress bar compatibility
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing documents"):
            try:
                res = await f # await the future to get result or raise exception
                results.append(res) # res will be None as process_single_document doesn't return anything significant
            except Exception as e:
                # Errors from process_single_document should be caught there,
                # but catch any unexpected errors from the task itself.
                _log.error(f"Error processing a document task: {e}", exc_info=True)

        processed_count = len(results) # Count how many tasks completed (even if they logged errors internally)
        _log.info(f"Finished processing folder. Attempted {len(tasks)} tasks, completed {processed_count}.")

    _log.info(f"Temporary directory {temp_dir_str} cleaned up.")
