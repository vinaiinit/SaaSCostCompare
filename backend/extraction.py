"""
Extraction pipeline: Convert uploaded files (CSV, PDF, ZIP) into
structured ContractLineItem rows in the database.

CSV → direct parse
PDF → AI structured extraction (Claude extracts rows, not analysis)
ZIP → unpack, then process each file
"""
import os
import json
import csv
import io
from datetime import datetime, date
from sqlalchemy.orm import Session

from models import ContractLineItem, Report, Organization
from vendor_normalization import normalize_line_item
from file_processor import extract_text_from_pdf, extract_text_from_docx, process_zip


def _parse_float(val) -> float:
    """Safely parse a float from various formats."""
    if val is None:
        return 0.0
    raw = str(val).replace("$", "").replace(",", "").replace(" ", "").strip()
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def _parse_int(val) -> int:
    """Safely parse an int from various formats."""
    if val is None:
        return 0
    raw = str(val).replace(",", "").replace(" ", "").strip()
    try:
        return int(float(raw))
    except (ValueError, TypeError):
        return 0


def _parse_date(val) -> date | None:
    """Try common date formats."""
    if not val or str(val).strip() == "":
        return None
    raw = str(val).strip()
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_billing_frequency(raw: str) -> str:
    """Map various billing frequency strings to canonical values."""
    if not raw:
        return "annual"
    lower = raw.strip().lower()
    if lower in ("monthly", "month", "per month", "mo"):
        return "monthly"
    if lower in ("annual", "annually", "yearly", "year", "per year", "yr"):
        return "annual"
    if lower in ("multi_year", "multi-year", "multiyear", "2-year", "3-year", "multi year"):
        return "multi_year"
    return "annual"


def compute_annual_costs(unit_price: float, total_cost: float, billing_freq: str,
                         start_date: date | None, end_date: date | None) -> tuple[float, float]:
    """
    Compute (cost_per_unit_annual, total_cost_annual) from raw values.
    """
    if billing_freq == "monthly":
        return unit_price * 12, total_cost * 12
    elif billing_freq == "multi_year" and start_date and end_date:
        days = (end_date - start_date).days
        years = max(days / 365.25, 0.5)  # at least half a year
        return unit_price / years, total_cost / years
    else:
        # annual or unknown — use as-is
        return unit_price, total_cost


# ── CSV extraction ───────────────────────────────────────────────────────────

def extract_from_csv(file_path: str, upload_id: str, org_id: int, db: Session) -> list[ContractLineItem]:
    """Parse CSV rows into ContractLineItem objects."""
    items = []
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalize keys to lowercase/stripped
                norm = {k.strip().lower(): v for k, v in row.items()}

                raw_vendor = norm.get("vendor", "").strip()
                raw_product = norm.get("product_name", "").strip()
                if not raw_vendor and not raw_product:
                    continue

                vendor, product = normalize_line_item(raw_vendor, raw_product, db)

                unit_price = _parse_float(norm.get("unit_price"))
                total_cost = _parse_float(norm.get("total_cost"))
                quantity = _parse_int(norm.get("quantity")) or 1
                billing_freq = _normalize_billing_frequency(norm.get("billing_frequency", ""))
                start_date = _parse_date(norm.get("contract_start_date"))
                end_date = _parse_date(norm.get("contract_end_date"))
                currency = norm.get("currency", "USD").strip().upper() or "USD"

                cost_per_unit_annual, total_cost_annual = compute_annual_costs(
                    unit_price, total_cost, billing_freq, start_date, end_date
                )

                item = ContractLineItem(
                    upload_id=upload_id,
                    org_id=org_id,
                    vendor_name=vendor,
                    product_name=product,
                    sku=norm.get("sku", "").strip() or None,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_cost=total_cost,
                    billing_frequency=billing_freq,
                    currency=currency,
                    contract_start_date=start_date,
                    contract_end_date=end_date,
                    cost_per_unit_annual=cost_per_unit_annual,
                    total_cost_annual=total_cost_annual,
                    extraction_source="csv",
                    extraction_confidence=1.0,
                )
                items.append(item)
    except Exception as e:
        print(f"Error extracting CSV {file_path}: {e}")
    return items


# ── PDF extraction (AI structured extraction) ────────────────────────────────

def extract_from_pdf(file_path: str, upload_id: str, org_id: int, db: Session) -> tuple[list[ContractLineItem], list[str]]:
    """
    Extract text from PDF, then use Claude to parse into structured line items.
    Returns (items, warnings).
    """
    warnings = []
    text = extract_text_from_pdf(file_path)
    basename = os.path.basename(file_path)

    if not text or len(text.strip()) < 50:
        warnings.append(
            f"{basename} appears to be a scanned/image-based PDF. "
            "No text could be extracted. Please upload a text-based PDF or CSV instead."
        )
        return [], warnings

    # Use Claude for structured extraction only
    items = _ai_extract_line_items(text, upload_id, org_id, db)

    if not items:
        warnings.append(
            f"{basename}: Could not extract structured line items from this PDF. "
            "The document may not contain tabular pricing data."
        )

    return items, warnings


# ── DOCX extraction (AI structured extraction) ─────────────────────────────

def extract_from_docx(file_path: str, upload_id: str, org_id: int, db: Session) -> tuple[list[ContractLineItem], list[str]]:
    """
    Extract text from Word document, then use Claude to parse into structured line items.
    Returns (items, warnings).
    """
    warnings = []
    text = extract_text_from_docx(file_path)
    basename = os.path.basename(file_path)

    if not text or len(text.strip()) < 50:
        warnings.append(
            f"{basename}: Very little text could be extracted from this Word document. "
            "Please ensure it contains tabular pricing data."
        )
        return [], warnings

    items = _ai_extract_line_items(text, upload_id, org_id, db)

    if not items:
        warnings.append(
            f"{basename}: Could not extract structured line items from this Word document. "
            "The document may not contain tabular pricing data."
        )

    return items, warnings


def _ai_extract_line_items(pdf_text: str, upload_id: str, org_id: int, db: Session) -> list[ContractLineItem]:
    """
    Call Claude to extract structured line items from PDF text.
    This is EXTRACTION only — Claude parses text into rows, no analysis.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""You are a contract data extraction tool. Given the following contract/invoice text,
extract every pricing line item into this exact JSON format:

[
  {{
    "vendor_name": "string",
    "product_name": "string",
    "sku": "string or null",
    "quantity": number,
    "unit_price": number,
    "total_cost": number,
    "billing_frequency": "monthly" or "annual" or "multi_year",
    "currency": "USD",
    "contract_start_date": "YYYY-MM-DD or null",
    "contract_end_date": "YYYY-MM-DD or null"
  }}
]

Rules:
- Extract numbers as plain numbers WITHOUT currency symbols (e.g. 99 not "USD 99").
- For vendor_name: if not explicitly stated, infer from product names (e.g. "Service Cloud" = "Salesforce", "M365" = "Microsoft", "S/4HANA" = "SAP", "EC2" = "AWS").
- For billing_frequency: "Monthly unit price" with a 12-month term means "monthly". Use the unit price as-is and set billing_frequency to "monthly".
- For total_cost: this is the total contract value for that line item.
- For dates: convert formats like "1/1/25" to "2025-01-01".
- If a field is not found, use null for optional fields and 0 for numeric fields.
- If you cannot find ANY pricing line items, return an empty array: []
- Return ONLY valid JSON, no other text, no markdown, no explanation.

CONTRACT TEXT:
{pdf_text[:6000]}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()

        # Strip markdown code fences if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:])
            if response_text.endswith("```"):
                response_text = response_text[:-3]

        parsed = json.loads(response_text)
        if not isinstance(parsed, list):
            return []

        items = []
        for row in parsed:
            raw_vendor = row.get("vendor_name", "").strip()
            raw_product = row.get("product_name", "").strip()
            if not raw_vendor and not raw_product:
                continue

            vendor, product = normalize_line_item(raw_vendor, raw_product, db)

            unit_price = _parse_float(row.get("unit_price"))
            total_cost = _parse_float(row.get("total_cost"))
            quantity = _parse_int(row.get("quantity")) or 1
            billing_freq = _normalize_billing_frequency(row.get("billing_frequency", "annual"))
            start_date = _parse_date(row.get("contract_start_date"))
            end_date = _parse_date(row.get("contract_end_date"))

            cost_per_unit_annual, total_cost_annual = compute_annual_costs(
                unit_price, total_cost, billing_freq, start_date, end_date
            )

            item = ContractLineItem(
                upload_id=upload_id,
                org_id=org_id,
                vendor_name=vendor,
                product_name=product,
                sku=row.get("sku") or None,
                quantity=quantity,
                unit_price=unit_price,
                total_cost=total_cost,
                billing_frequency=billing_freq,
                currency=row.get("currency", "USD") or "USD",
                contract_start_date=start_date,
                contract_end_date=end_date,
                cost_per_unit_annual=cost_per_unit_annual,
                total_cost_annual=total_cost_annual,
                extraction_source="pdf_ai",
                extraction_confidence=0.8,
            )
            items.append(item)
        return items

    except Exception as e:
        import traceback
        print(f"AI extraction error: {e}")
        traceback.print_exc()
        return []


# ── Main extraction pipeline ─────────────────────────────────────────────────

def run_extraction(upload_id: str, file_path: str, org_id: int, db: Session) -> dict:
    """
    Main extraction entry point. Process all files for an upload,
    extract structured line items, store in DB.

    file_path can be a local directory or an s3:// URI.
    Returns: {"line_items_count": int, "warnings": [...], "file_summary": str}
    """
    import shutil
    from s3_storage import download_to_temp

    report = db.query(Report).filter(Report.id == upload_id).first()
    if not report:
        return {"error": "Upload not found"}

    report.status = "extracting"
    db.commit()

    # Download from S3 to temp dir if needed
    is_s3 = file_path.startswith("s3://")
    local_path = download_to_temp(file_path) if is_s3 else file_path

    all_items = []
    all_warnings = []
    file_names = []

    try:
        # Collect all files to process
        files_to_process = []
        if os.path.isdir(local_path):
            for root, dirs, files in os.walk(local_path):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    lower = fname.lower()
                    if lower.endswith((".csv", ".pdf", ".doc", ".docx")):
                        files_to_process.append(fpath)
                    elif lower.endswith(".zip"):
                        extracted = process_zip(fpath, root)
                        files_to_process.extend(extracted)
        elif os.path.isfile(local_path):
            files_to_process.append(local_path)

        # Process each file
        for fpath in files_to_process:
            basename = os.path.basename(fpath)
            lower = fpath.lower()

            if lower.endswith(".csv"):
                items = extract_from_csv(fpath, upload_id, org_id, db)
                all_items.extend(items)
                file_names.append(f"{basename} (CSV, {len(items)} rows)")

            elif lower.endswith(".pdf"):
                items, warnings = extract_from_pdf(fpath, upload_id, org_id, db)
                all_items.extend(items)
                all_warnings.extend(warnings)
                file_names.append(f"{basename} (PDF, {len(items)} items extracted)")

            elif lower.endswith((".doc", ".docx")):
                items, warnings = extract_from_docx(fpath, upload_id, org_id, db)
                all_items.extend(items)
                all_warnings.extend(warnings)
                file_names.append(f"{basename} (Word, {len(items)} items extracted)")

        # Store all line items in DB
        for item in all_items:
            db.add(item)

        file_summary = "; ".join(file_names) if file_names else "No files processed"

        # Update report
        report.status = "extracted"
        report.comparison_result = json.dumps({
            "extraction_summary": {
                "line_items_count": len(all_items),
                "file_summary": file_summary,
                "extracted_at": str(datetime.now()),
            },
            "warnings": all_warnings,
        })
        db.commit()

    finally:
        # Clean up temp directory if we downloaded from S3
        if is_s3 and os.path.isdir(local_path):
            shutil.rmtree(local_path, ignore_errors=True)

    return {
        "line_items_count": len(all_items),
        "warnings": all_warnings,
        "file_summary": file_summary,
    }
