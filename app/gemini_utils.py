import json
import re
import logging
import google.generativeai as genai

# Get logger and config from parent package
try:
    from .config import _log, MAX_GEMINI_INPUT_LENGTH
    from .schemas import (
        BANK_STATEMENT_SCHEMA,
        PURCHASE_INVOICE_SCHEMA,
        SALES_INVOICE_SCHEMA,
        RECEIPT_SCHEMA,
        PURCHASE_ORDER_SCHEMA,
        CHALLAN_SCHEMA,
        SIMPLE_TEXT_SCHEMA
    )
except ImportError:
    # Fallback for standalone execution or testing
    logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    MAX_GEMINI_INPUT_LENGTH = 30000 # Default if config not loaded

def clean_invalid_json(content: str) -> str:
    """Removes markdown code fences and potentially other unwanted chars from Gemini output."""
    # Remove markdown fences
    content = re.sub(r"```json", "", content, flags=re.IGNORECASE)
    content = re.sub(r"```", "", content)
    # Strip leading/trailing whitespace
    content = content.strip()
    # Add more cleaning rules here if needed (e.g., remove leading/trailing commas, fix quotes)
    return content

async def classify_and_extract_with_gemini(content: str, is_multi_page: bool) -> tuple[str, dict]:
    """
    Uses Gemini to classify the document and extract data accordingly.

    Args:
        content: The text content extracted from the document (potentially truncated).
        is_multi_page: Boolean indicating if the original document had multiple pages.

    Returns:
        A tuple containing:
            - str: The classification ('bank_statement', 'simple_text', 'purchase_invoice', 'sales_invoice', 'receipt', 'purchase_order', 'challan').
            - dict: The extracted JSON data (based on the document type).
    """
    _log.info(f"Sending content (first {min(len(content), 50)} chars) to Gemini for classification/extraction.")
    try:
        # Consider using a specific model version if needed
        # model = genai.GenerativeModel("gemini-1.5-flash-001")
        model = genai.GenerativeModel("gemini-1.5-flash") # Use a fast model
        page_context = "the first page of a multi-page document" if is_multi_page else "a single-page document"

        # Limit content length sent to Gemini
        truncated_content = content[:MAX_GEMINI_INPUT_LENGTH]
        if len(content) > MAX_GEMINI_INPUT_LENGTH:
            _log.warning(f"Content truncated to {MAX_GEMINI_INPUT_LENGTH} characters for Gemini classification prompt.")

        prompt = f"""
        Analyze the following content from {page_context}.
        First, determine the document type. It can be one of the following:
        - bank_statement
        - simple_text
        - purchase_invoice
        - sales_invoice
        - receipt
        - purchase_order
        - challan
        Respond with a JSON object containing two keys:
        1. "document_type": Set this to the determined document type (one of the options above).
        2. "extracted_data":
           - If "document_type" is "bank_statement", extract the data into a JSON object matching this structure:
             {json.dumps(BANK_STATEMENT_SCHEMA)}
           - If "document_type" is "simple_text", set "extracted_data" to a JSON object containing the raw text like this:
             {json.dumps(SIMPLE_TEXT_SCHEMA)}
           - If "document_type" is "purchase_invoice", extract the data into a JSON object matching this structure:
             {json.dumps(PURCHASE_INVOICE_SCHEMA)}
           - If "document_type" is "sales_invoice", extract the data into a JSON object matching this structure:
             {json.dumps(SALES_INVOICE_SCHEMA)}
           - If "document_type" is "receipt", extract the data into a JSON object matching this structure:
             {json.dumps(RECEIPT_SCHEMA)}
           - If "document_type" is "purchase_order", extract the data into a JSON object matching this structure:
             {json.dumps(PURCHASE_ORDER_SCHEMA)}
           - If "document_type" is "challan", extract the data into a JSON object matching this structure:
             {json.dumps(CHALLAN_SCHEMA)}

        Content to analyze:
        \"\"\"{truncated_content}\"\"\"

        Return ONLY the JSON object. Do not include any other text or markdown formatting. Ensure the JSON is valid.
        """

        response = await model.generate_content_async(prompt)
        reply = response.text
        cleaned_json_str = clean_invalid_json(reply)

        # Attempt to parse the JSON
        try:
            gemini_output = json.loads(cleaned_json_str)
            if not isinstance(gemini_output, dict):
                 raise json.JSONDecodeError("Response is not a JSON object", cleaned_json_str, 0)
        except json.JSONDecodeError as json_err:
            _log.error(f"Failed to decode Gemini JSON response: {json_err}")
            _log.error(f"Problematic JSON string from Gemini: {cleaned_json_str}")
            # Fallback: Assume simple text if JSON parsing fails
            return "simple_text", {"extracted_text": content} # Return original full content

        # Process the parsed JSON
        doc_type = gemini_output.get("document_type", "simple_text").lower()
        extracted_data = gemini_output.get("extracted_data", {})

        # Basic validation and fallback logic
        if doc_type == "bank_statement":
            if not isinstance(extracted_data, dict) or not isinstance(extracted_data.get("transactions"), list):
                _log.warning(f"Gemini classified as bank_statement but 'extracted_data' is invalid or 'transactions' is not a list. Falling back to simple_text.")
                doc_type = "simple_text"
                extracted_data = {"extracted_text": content} # Return original full content
            # Optional: Add jsonschema validation here using BANK_STATEMENT_SCHEMA
        elif doc_type == "simple_text":
            if not isinstance(extracted_data, dict) or "extracted_text" not in extracted_data:
                _log.warning(f"Gemini classified as simple_text but 'extracted_data' is invalid or 'extracted_text' key is missing. Using original content.")
                # Ensure extracted_data is a dict with the correct key
                extracted_data = {"extracted_text": content} # Return original full content
        elif doc_type == "purchase_invoice":
            if not isinstance(extracted_data, dict) or not all(key in extracted_data for key in PURCHASE_INVOICE_SCHEMA["required"]):
                _log.warning(f"Gemini classified as purchase_invoice but 'extracted_data' is missing required fields. Falling back to simple_text.")
                doc_type = "simple_text"
                extracted_data = {"extracted_text": content}
        elif doc_type == "sales_invoice":
            if not isinstance(extracted_data, dict) or not all(key in extracted_data for key in SALES_INVOICE_SCHEMA["required"]):
                _log.warning(f"Gemini classified as sales_invoice but 'extracted_data' is missing required fields. Falling back to simple_text.")
                doc_type = "simple_text"
                extracted_data = {"extracted_text": content}
        elif doc_type == "receipt":
            if not isinstance(extracted_data, dict) or not all(key in extracted_data for key in RECEIPT_SCHEMA["required"]):
                _log.warning(f"Gemini classified as receipt but 'extracted_data' is missing required fields. Falling back to simple_text.")
                doc_type = "simple_text"
                extracted_data = {"extracted_text": content}
        elif doc_type == "purchase_order":
            if not isinstance(extracted_data, dict) or not all(key in extracted_data for key in PURCHASE_ORDER_SCHEMA["required"]):
                _log.warning(f"Gemini classified as purchase_order but 'extracted_data' is missing required fields. Falling back to simple_text.")
                doc_type = "simple_text"
                extracted_data = {"extracted_text": content}
        elif doc_type == "challan":
            if not isinstance(extracted_data, dict) or not all(key in extracted_data for key in CHALLAN_SCHEMA["required"]):
                _log.warning(f"Gemini classified as challan but 'extracted_data' is missing required fields. Falling back to simple_text.")
                doc_type = "simple_text"
                extracted_data = {"extracted_text": content}
        else:
            _log.warning(f"Gemini returned unknown document_type: {doc_type}. Defaulting to simple_text.")
            doc_type = "simple_text"
            extracted_data = {"extracted_text": content} # Use original full content

        _log.info(f"Gemini classification result: {doc_type}")
        return doc_type, extracted_data

    except Exception as e:
        # Catch potential API errors, network issues, etc.
        _log.error(f"Error interacting with Gemini API for classification/extraction: {e}", exc_info=True)
        # Fallback: Assume simple text on any Gemini error
        return "simple_text", {"extracted_text": content}


async def extract_full_bank_statement_with_gemini(full_content: str) -> dict:
    """
    Uses Gemini (potentially a more powerful model) to extract structured data
    from the full text of a document already classified as a bank statement.

    Args:
        full_content: The complete text extracted from the bank statement PDF.

    Returns:
        dict: The extracted bank statement data, or an empty dict on failure.
    """
    _log.info(f"Sending full bank statement content (length: {len(full_content)}) to Gemini for detailed extraction.")
    try:
        # Use a potentially more capable model for full extraction if needed
        # model = genai.GenerativeModel("gemini-1.5-pro-latest")
        model = genai.GenerativeModel("gemini-1.5-pro") # Or stick with flash if sufficient

        # Limit input length if necessary, though Pro models handle more
        # truncated_content = full_content[:100000] # Example limit for Pro

        prompt = f"""
        You are an expert assistant specialized in extracting structured data from bank statements.
        Convert the following full bank statement content into a JSON object matching this exact structure:
        {json.dumps(BANK_STATEMENT_SCHEMA)}
        Ensure all relevant fields are populated accurately based on the content. Pay close attention to extracting all transactions listed.

        Full Bank statement content:
        \"\"\"{full_content}\"\"\"

        Return ONLY the JSON object. Ensure it is valid JSON. Do not include any explanations or markdown formatting.
        """

        response = await model.generate_content_async(prompt)
        reply = response.text
        cleaned_json_str = clean_invalid_json(reply)

        # Attempt to parse the JSON
        try:
            extracted_json = json.loads(cleaned_json_str)
            if not isinstance(extracted_json, dict):
                 raise json.JSONDecodeError("Response is not a JSON object", cleaned_json_str, 0)
            # Optional: Validate against BANK_STATEMENT_SCHEMA here
            _log.info("Successfully extracted full bank statement data from Gemini.")
            return extracted_json
        except json.JSONDecodeError as json_err:
            _log.error(f"Failed to decode full bank statement JSON from Gemini: {json_err}")
            _log.error(f"Problematic JSON string: {cleaned_json_str}")
            return {} # Return empty dict on failure

    except Exception as e:
        _log.error(f"Error interacting with Gemini API for full bank statement extraction: {e}", exc_info=True)
        return {} # Return empty dict on failure
