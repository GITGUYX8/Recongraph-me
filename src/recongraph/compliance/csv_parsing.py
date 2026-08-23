"""CSV ingestion helpers that understand the extended GST field set (F3).

Shared by the CLI and the FastAPI layer so both accept the same optional
columns (place_of_supply, reverse charge, tax heads, IRN, classification, etc.)
without breaking the original minimal schema.
"""

import csv
import io
import uuid
from datetime import date
from decimal import Decimal
from typing import Iterable

from recongraph.domain.records import PurchaseRecord, GSTRecord

_BOOL_TRUE = {"1", "true", "yes", "y", "t"}
_BOOL_FALSE = {"0", "false", "no", "n", "f"}


def _get(row: dict, *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return None


def _decimal(row: dict, *keys: str) -> Decimal | None:
    value = _get(row, *keys)
    if value is None:
        return None
    try:
        return Decimal(value)
    except Exception:
        return None


def _bool(row: dict, *keys: str) -> bool | None:
    value = _get(row, *keys)
    if value is None:
        return None
    lowered = value.lower()
    if lowered in _BOOL_TRUE:
        return True
    if lowered in _BOOL_FALSE:
        return False
    return None


def _date(row: dict, *keys: str) -> date:
    value = _get(row, *keys)
    if value is None:
        return date(2000, 1, 1)
    try:
        return date.fromisoformat(value)
    except ValueError:
        return date(2000, 1, 1)


def parse_purchase_csv(content: str) -> list[PurchaseRecord]:
    return [_purchase_from_row(row) for row in csv.DictReader(io.StringIO(content))]


def parse_gst_csv(content: str) -> list[GSTRecord]:
    return [_gst_from_row(row) for row in csv.DictReader(io.StringIO(content))]


def parse_purchase_rows(rows: Iterable[dict]) -> list[PurchaseRecord]:
    return [_purchase_from_row(row) for row in rows]


def parse_gst_rows(rows: Iterable[dict]) -> list[GSTRecord]:
    return [_gst_from_row(row) for row in rows]


def _purchase_from_row(row: dict) -> PurchaseRecord:
    return PurchaseRecord(
        record_id=_get(row, "record_id", "id") or f"auto_{uuid.uuid4().hex[:8]}",
        vendor_name=_get(row, "vendor_name", "supplier_name"),
        reference=_get(row, "reference", "invoice_number", "bill_no"),
        amount=_decimal(row, "amount") or Decimal("0"),
        record_date=_date(row, "record_date", "invoice_date", "bill_date"),
        tax_identity=_get(row, "gstin", "tax_identity", "supplier_gstin"),
        place_of_supply=_get(row, "place_of_supply"),
        is_reverse_charge=_bool(row, "is_reverse_charge", "reverse_charge"),
        document_type=_get(row, "document_type", "doctype"),
        is_return=_bool(row, "is_return"),
        amendment_type=_get(row, "amendment_type"),
        fiscal_year=_get(row, "fiscal_year"),
        company_gstin=_get(row, "company_gstin", "buyer_gstin"),
        taxable_value=_decimal(row, "taxable_value"),
        cgst=_decimal(row, "cgst"),
        sgst=_decimal(row, "sgst"),
        igst=_decimal(row, "igst"),
        cess=_decimal(row, "cess"),
        irn_number=_get(row, "irn_number"),
        irn_source=_get(row, "irn_source"),
        classification=_get(row, "classification"),
    )


def _gst_from_row(row: dict) -> GSTRecord:
    return GSTRecord(
        record_id=_get(row, "record_id", "id") or f"auto_{uuid.uuid4().hex[:8]}",
        vendor_name=_get(row, "vendor_name", "supplier_name"),
        reference=_get(row, "reference", "invoice_number", "bill_no"),
        amount=_decimal(row, "amount") or Decimal("0"),
        record_date=_date(row, "record_date", "invoice_date", "bill_date"),
        tax_identity=_get(row, "gstin", "tax_identity", "supplier_gstin"),
        place_of_supply=_get(row, "place_of_supply"),
        is_reverse_charge=_bool(row, "is_reverse_charge", "reverse_charge"),
        document_type=_get(row, "document_type", "doctype"),
        is_return=_bool(row, "is_return"),
        amendment_type=_get(row, "amendment_type"),
        fiscal_year=_get(row, "fiscal_year"),
        company_gstin=_get(row, "company_gstin", "buyer_gstin"),
        taxable_value=_decimal(row, "taxable_value"),
        cgst=_decimal(row, "cgst"),
        sgst=_decimal(row, "sgst"),
        igst=_decimal(row, "igst"),
        cess=_decimal(row, "cess"),
        irn_number=_get(row, "irn_number"),
        irn_source=_get(row, "irn_source"),
        classification=_get(row, "classification"),
    )
