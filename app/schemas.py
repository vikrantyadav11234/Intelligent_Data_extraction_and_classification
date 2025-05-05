from pydantic import BaseModel
from typing import Optional, List, Dict, Union
from datetime import date, datetime

# --- JSON Schemas ---
PURCHASE_INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "purchase_invoice_number": {"type": "string"},
        "purchase_invoice_date": {"type": "string", "format": "date"},
        "currency": {"type": "string"},
        "reverse_charge": {"type": "string"},
        "import_purchase": {"type": "boolean"},
        "vendor": {"type": "object"},
        "buyer": {"type": "object"},
        "purchase_order_reference": {"type": "object"},
        "delivery_note_number": {"type": ["string", "null"]},
        "eway_bill_number": {"type": ["string", "null"]},
        "bill_of_entry_number": {"type": ["string", "null"]},
        "items": {
            "type": "array",
            "items": {"type": "object"}
        },
        "totals": {"type": "object"},
        "payment_terms": {"type": "object"},
        "delivery_terms": {"type": "object"},
        "remarks": {"type": "string"},
        "authorized_signatory": {"type": "object"},
        "attachments": {
            "type": "array",
            "items": {"type": "object"}
        },
        "compliance": {"type": "object"},
        "audit_trail": {
            "type": "array",
            "items": {"type": "object"}
        }
    },
    "required": [
        "purchase_invoice_number",
        "purchase_invoice_date",
        "currency",
        "reverse_charge",
        "import_purchase",
        "vendor",
        "buyer",
        "items",
        "totals",
        "payment_terms",
        "authorized_signatory"
    ]
}
SALES_INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "sales_invoice_number": {"type": "string"},
        "sales_invoice_date": {"type": "string", "format": "date"},
        "currency": {"type": "string"},
        "reverse_charge": {"type": "string"},
        "import_sale": {"type": "boolean"},
        "vendor": {"type": "object"},
        "buyer": {"type": "object"},
        "sales_order_reference": {"type": "object"},
        "delivery_note_number": {"type": ["string", "null"]},
        "eway_bill_number": {"type": ["string", "null"]},
        "bill_of_entry_number": {"type": ["string", "null"]},
        "items": {
            "type": "array",
            "items": {"type": "object"}
        },
        "totals": {"type": "object"},
        "payment_terms": {"type": "object"},
        "delivery_terms": {"type": "object"},
        "remarks": {"type": "string"},
        "authorized_signatory": {"type": "object"},
        "attachments": {
            "type": "array",
            "items": {"type": "object"}
        },
        "compliance": {"type": "object"},
        "audit_trail": {
            "type": "array",
            "items": {"type": "object"}
        }
    },
    "required": [
        "sales_invoice_number",
        "sales_invoice_date",
        "currency",
        "reverse_charge",
        "import_sale",
        "vendor",
        "buyer",
        "items",
        "totals",
        "payment_terms",
        "authorized_signatory"
    ]
}

RECEIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "receipt_number": {"type": "string"},
        "receipt_date": {"type": "string", "format": "date"},
        "receipt_type": {"type": "string", "enum": ["cash", "bank_transfer", "cheque", "online", "other"]},
        "currency": {"type": "string"},
        "payment_method": {"type": "string"},
        "payment_date": {"type": "string", "format": "date"},
        "transaction_reference_number": {"type": "string"},
        "payer": {"type": "object"},
        "payee": {"type": "object"},
        "amount_paid": {"type": "number"},
        "gst_amount": {"type": "number"},
        "items": {
            "type": "array",
            "items": {"type": "object"}
        },
        "remarks": {"type": "string"},
        "receipt_status": {"type": "string", "enum": ["paid", "pending", "cancelled"]},
        "authorized_signatory": {"type": "object"},
        "attachments": {
            "type": "array",
            "items": {"type": "object"}
        },
        "compliance": {"type": "object"},
        "audit_trail": {
            "type": "array",
            "items": {"type": "object"}
        }
    },
    "required": [
        "receipt_number",
        "receipt_date",
        "receipt_type",
        "currency",
        "payment_method",
        "payer",
        "payee",
        "amount_paid",
        "gst_amount",
        "items",
        "receipt_status",
        "authorized_signatory"
    ]
}

PURCHASE_ORDER_SCHEMA = {
    "type": "object",
    "properties": {
        "purchase_order_number": {"type": "string"},
        "purchase_order_date": {"type": "string", "format": "date"},
        "buyer": {"type": "object"},
        "supplier": {"type": "object"},
        "delivery_address": {"type": "object"},
        "items": {
            "type": "array",
            "items": {"type": "object"}
        },
        "payment_terms": {"type": "string"},
        "delivery_terms": {"type": "string"},
        "total_amount": {"type": "number"},
        "currency": {"type": "string"},
        "authorized_signatory": {"type": "object"},
        "remarks": {"type": "string"},
        "attachments": {
            "type": "array",
            "items": {"type": "object"}
        },
        "audit_trail": {
            "type": "array",
            "items": {"type": "object"}
        },
        "gstin": {"type": "string"},  # GST number of the buyer
        "buyer_account_number": {"type": "string"},  # Buyer’s account number for payment
        "supplier_account_number": {"type": "string"},  # Supplier’s account number for payment
        "supplier_gstin": {"type": "string"},  # GST number of the supplier
        "shipping_address": {"type": "object"},  # Shipping address (could be different from delivery address)
        "order_reference": {"type": "string"},  # Reference or PO reference number
        "contact_details": {"type": "object"},  # Contact details of buyer and seller (email, phone)
        "discount": {"type": "number"}  # Any discount applied to the order
    },
    "required": [
        "purchase_order_number",
        "purchase_order_date",
        "buyer",
        "supplier",
        "items",
        "total_amount",
        "currency",
        "authorized_signatory"
    ]
}
CHALLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "challan_number": {"type": "string"},
        "challan_date": {"type": "string", "format": "date"},
        "challan_type": {"type": "string"},  # e.g. Delivery, Return, Job Work etc.
        "reference_document": {"type": "object"},
        "vendor": {"type": "object"},
        "buyer": {"type": "object"},
        "dispatch_details": {"type": "object"},
        "items": {
            "type": "array",
            "items": {"type": "object"}
        },
        "totals": {"type": "object"},
        "eway_bill_number": {"type": "string"},
        "remarks": {"type": "string"},
        "authorized_signatory": {"type": "object"},
        "attachments": {
            "type": "array",
            "items": {"type": "object"}
        },
        "audit_trail": {
            "type": "array",
            "items": {"type": "object"}
        },
        "gstin": {"type": "string"},  # Vendor GSTIN
        "buyer_gstin": {"type": "string"},  # Buyer GSTIN
        "dispatch_from": {"type": "object"},  # From address
        "dispatch_to": {"type": "object"},  # To address
        "vehicle_number": {"type": "string"},  # Transport vehicle details
        "transporter_name": {"type": "string"},  # Name of the transporter
        "transporter_gstin": {"type": "string"},  # GSTIN of transporter if applicable
        "delivery_terms": {"type": "string"}  # E.g. "FOB", "Door Delivery"
    },
    "required": [
        "challan_number",
        "challan_date",
        "challan_type",
        "vendor",
        "buyer",
        "items"
    ]
}

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
    
class PurchaseInvoiceOutput(BaseModel):
    purchase_invoice_number: str
    purchase_invoice_date: date
    currency: str
    reverse_charge: str
    import_purchase: bool
    vendor: dict
    buyer: dict
    purchase_order_reference: Optional[dict] = None
    delivery_note_number: Optional[str] = None
    eway_bill_number: Optional[str] = None
    bill_of_entry_number: Optional[str] = None
    items: List[dict]
    totals: dict
    payment_terms: dict
    delivery_terms: Optional[dict] = None
    remarks: Optional[str] = None
    authorized_signatory: dict
    attachments: Optional[List[dict]] = None
    compliance: Optional[dict] = None
    audit_trail: Optional[List[dict]] = None
    
class SalesInvoiceOutput(BaseModel):
    sales_invoice_number: str
    sales_invoice_date: date
    currency: str
    reverse_charge: str
    import_sale: bool
    vendor: dict
    buyer: dict
    sales_order_reference: Optional[dict] = None
    delivery_note_number: Optional[str] = None
    eway_bill_number: Optional[str] = None
    bill_of_entry_number: Optional[str] = None
    items: List[dict]
    totals: dict
    payment_terms: dict
    delivery_terms: Optional[dict] = None
    remarks: Optional[str] = None
    authorized_signatory: dict
    attachments: Optional[List[dict]] = None
    compliance: Optional[dict] = None
    audit_trail: Optional[List[dict]] = None
    
class ReceiptOutput(BaseModel):
    receipt_number: str
    receipt_date: date
    receipt_type: str  # Example values: 'cash', 'bank_transfer', 'cheque', 'online', 'other'
    currency: str
    payment_method: str
    payment_date: Optional[date] = None  # If payment_date is available
    transaction_reference_number: Optional[str] = None  # Optional reference for transactions like cheque or bank transfer
    payer: dict
    payee: dict
    amount_paid: float
    gst_amount: float
    items: List[dict]
    remarks: Optional[str] = None
    receipt_status: str  # Example values: 'paid', 'pending', 'cancelled'
    authorized_signatory: dict
    attachments: Optional[List[dict]] = None
    compliance: Optional[dict] = None
    audit_trail: Optional[List[dict]] = None

class PurchaseOrderOutput(BaseModel):
    purchase_order_number: str
    purchase_order_date: date
    buyer: dict
    supplier: dict
    delivery_address: dict
    items: List[dict]
    payment_terms: Optional[str] = None  # Payment conditions, e.g., Net 30, advance payment, etc.
    delivery_terms: Optional[str] = None  # Delivery terms, e.g., FOB, CIF, etc.
    total_amount: float
    currency: str
    authorized_signatory: dict
    remarks: Optional[str] = None  # Optional remarks for the PO.
    attachments: Optional[List[dict]] = None  # Optional, for any supporting documents.
    audit_trail: Optional[List[dict]] = None  # Optional, for tracking the document changes.
    gstin: Optional[str] = None  # GST number of the buyer
    buyer_account_number: Optional[str] = None  # Buyer’s account number for payment
    supplier_account_number: Optional[str] = None  # Supplier’s account number for payment
    supplier_gstin: Optional[str] = None  # GST number of the supplier
    shipping_address: Optional[dict] = None  # Shipping address (could be different from delivery address)
    order_reference: Optional[str] = None  # Reference or PO reference number
    contact_details: Optional[dict] = None  # Contact details of buyer and seller (email, phone)
    discount: Optional[float] = None  # Any discount applied to the order
    
class ChallanOutput(BaseModel):
    challan_number: str
    challan_date: date
    challan_type: str  # e.g. Delivery, Return, Job Work etc.
    reference_document: Optional[dict] = None  # Related PO/Invoice
    vendor: dict
    buyer: dict
    dispatch_details: Optional[dict] = None
    items: List[dict]
    totals: Optional[dict] = None
    eway_bill_number: Optional[str] = None
    remarks: Optional[str] = None
    authorized_signatory: Optional[dict] = None
    attachments: Optional[List[dict]] = None
    audit_trail: Optional[List[dict]] = None
    gstin: Optional[str] = None  # Vendor GSTIN
    buyer_gstin: Optional[str] = None  # Buyer GSTIN
    dispatch_from: Optional[dict] = None  # Dispatch origin address
    dispatch_to: Optional[dict] = None  # Delivery destination address
    vehicle_number: Optional[str] = None  # Transport vehicle details
    transporter_name: Optional[str] = None  # Name of the transporter
    transporter_gstin: Optional[str] = None  # GSTIN of transporter
    delivery_terms: Optional[str] = None  # E.g. FOB, Door Delivery

class SimpleTextOutput(BaseModel):
    file_name: str
    extracted_text: str
