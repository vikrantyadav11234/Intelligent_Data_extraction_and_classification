from pydantic import BaseModel

# --- JSON Schemas ---
BANK_STATEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "account_holder": {"type": "object"},
        "bank_details": {"type": "object"},
        "account_summary": {"type": "object"},
        "transactions": {
            "type": "array",
            "items": {"type": "object"}
        }
    },
    "required": ["account_holder", "bank_details", "account_summary", "transactions"]
}

SIMPLE_TEXT_SCHEMA = {
    "type": "object",
    "properties": {
        "file_name": {"type": "string"},
        "extracted_text": {"type": "string"}
    },
    "required": ["file_name", "extracted_text"]
}

# --- Pydantic Models ---

# Input schema for folder processing API endpoint
class ProcessFolderRequest(BaseModel):
    input_folder: str
    output_folder: str

# Potentially add models for the output structures if needed for validation or response models
class BankStatementOutput(BaseModel):
    account_holder: dict | None = None
    bank_details: dict | None = None
    account_summary: dict | None = None
    transactions: list[dict] | None = None

class SimpleTextOutput(BaseModel):
    file_name: str
    extracted_text: str
