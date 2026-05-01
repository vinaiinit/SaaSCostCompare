from __future__ import annotations

"""
Extraction pipeline: Convert uploaded files (CSV, PDF, ZIP) into
structured ContractLineItem rows in the database.

CSV → direct parse
PDF → AI structured extraction (Claude extracts rows, not analysis)
ZIP → unpack, then process each file
"""
import os
import re
import json
import csv
import io
import base64
from datetime import datetime, date
from sqlalchemy.orm import Session

from models import ContractLineItem, Report, Organization
from vendor_normalization import normalize_line_item
from file_processor import extract_text_from_pdf, extract_text_from_docx, process_zip, extract_pages_from_pdf


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


# ── Page scoring & chunking for large PDFs ─────────────────────────────────

_PRICING_KEYWORDS = [
    'price', 'cost', 'total', 'amount', 'fee', 'charge',
    'quantity', 'qty', 'unit', 'annual', 'monthly', 'yearly',
    'subscription', 'license', 'licence', 'per user', 'per seat',
    'discount', 'subtotal', 'grand total', 'invoice',
    'quotation', 'quote', 'order form', 'line item',
    'extended', 'net', 'gross', 'rate', 'sku', 'part number',
]


def _score_page_for_pricing(text: str) -> float:
    """Score a page's likelihood of containing pricing data."""
    if not text:
        return 0.0
    lower = text.lower()
    score = 0.0
    for kw in _PRICING_KEYWORDS:
        score += lower.count(kw) * 2
    score += len(re.findall(r'\$[\d,]+\.?\d*', text)) * 3
    score += len(re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b', text)) * 1.5
    score += text.count('|') * 0.5
    return score


def _build_pricing_chunks(pages: list, max_chars_per_chunk: int = 5000, max_chunks: int = 8) -> list:
    """Select top pricing-relevant pages and group into chunks."""
    scored = [(p, _score_page_for_pricing(p["text"])) for p in pages]
    relevant = [(p, s) for p, s in scored if s > 2]

    if not relevant:
        all_text = "\n".join(p["text"] for p in pages if p["text"])
        return [all_text[:max_chars_per_chunk * 2]]

    relevant.sort(key=lambda x: x[1], reverse=True)

    selected = []
    total_chars = 0
    for p, s in relevant:
        if total_chars + len(p["text"]) > max_chars_per_chunk * max_chunks:
            break
        selected.append(p)
        total_chars += len(p["text"])

    selected.sort(key=lambda p: p["page"])

    chunks = []
    current_pages = []
    current_size = 0
    for p in selected:
        if current_size + len(p["text"]) > max_chars_per_chunk and current_pages:
            chunks.append("\n\n".join(
                f"[Page {cp['page']}]\n{cp['text']}" for cp in current_pages
            ))
            current_pages = []
            current_size = 0
        current_pages.append(p)
        current_size += len(p["text"])
    if current_pages:
        chunks.append("\n\n".join(
            f"[Page {cp['page']}]\n{cp['text']}" for cp in current_pages
        ))

    return chunks[:max_chunks]


def _ai_extract_chunked(chunks: list, upload_id: str, org_id: int, db: Session) -> list:
    """Extract line items from multiple text chunks and merge results."""
    all_items = []
    for i, chunk in enumerate(chunks):
        print(f"Extracting chunk {i + 1}/{len(chunks)} ({len(chunk)} chars)...")
        items = _ai_extract_line_items(chunk, upload_id, org_id, db)
        all_items.extend(items)
    return _dedup_items(all_items)


def _dedup_items(items: list) -> list:
    """Remove duplicate line items based on key fields."""
    seen = set()
    unique = []
    for item in items:
        key = (
            (item.vendor_name or "").lower(),
            (item.product_name or "").lower(),
            item.quantity,
            item.unit_price,
        )
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


# ── PDF extraction (AI structured extraction) ────────────────────────────────

def extract_from_pdf(file_path: str, upload_id: str, org_id: int, db: Session) -> tuple[list[ContractLineItem], list[str]]:
    """
    Extract text from PDF, then use Claude to parse into structured line items.
    Falls back to sending the raw PDF to Claude's vision API if text extraction fails.
    Returns (items, warnings).
    """
    warnings = []
    basename = os.path.basename(file_path)

    # Try text-based extraction first
    text = extract_text_from_pdf(file_path)
    meaningful = text.replace("|", "").replace("-", "").replace(" ", "").replace("\n", "")

    items = []
    if text and len(meaningful) >= 30:
        if len(text) > 12000:
            pages = extract_pages_from_pdf(file_path)
            if pages:
                chunks = _build_pricing_chunks(pages)
                print(f"Large PDF detected ({len(text)} chars, {len(pages)} pages) — "
                      f"using chunked extraction with {len(chunks)} chunk(s)")
                items = _ai_extract_chunked(chunks, upload_id, org_id, db)

        if not items:
            items = _ai_extract_line_items(text, upload_id, org_id, db)

    # If text extraction produced nothing, fall back to vision-based PDF reading
    if not items:
        print(f"Text extraction failed for {basename}, trying vision-based PDF extraction...")
        items = _ai_extract_from_pdf_file(file_path, upload_id, org_id, db)

    if not items:
        warnings.append(
            f"{basename}: Could not extract structured line items from this PDF. "
            "The document may not contain tabular pricing data. "
            "This may be due to a temporary API error — please try uploading again."
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
{pdf_text[:12000]}"""

    import time
    last_err = None
    for attempt in range(3):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            break
        except Exception as api_err:
            last_err = api_err
            print(f"AI extraction attempt {attempt + 1} failed: {api_err}")
            if attempt < 2:
                time.sleep(2 ** attempt)
    else:
        print(f"AI extraction failed after 3 attempts: {last_err}")
        return []

    try:
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


_VISION_EXTRACTION_PROMPT = """You are a contract data extraction tool. Look at this document and
extract every pricing line item into this exact JSON format:

[
  {
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
  }
]

Rules:
- Extract numbers as plain numbers WITHOUT currency symbols (e.g. 99 not "USD 99").
- For vendor_name: if not explicitly stated, infer from product names (e.g. "Service Cloud" = "Salesforce", "M365" = "Microsoft", "S/4HANA" = "SAP", "EC2" = "AWS").
- For billing_frequency: "Monthly unit price" with a 12-month term means "monthly". Use the unit price as-is and set billing_frequency to "monthly".
- For total_cost: this is the total contract value for that line item.
- For dates: convert formats like "1/1/25" to "2025-01-01".
- If a field is not found, use null for optional fields and 0 for numeric fields.
- If you cannot find ANY pricing line items, return an empty array: []
- Return ONLY valid JSON, no other text, no markdown, no explanation."""


def _ai_extract_from_pdf_file(file_path: str, upload_id: str, org_id: int, db: Session) -> list[ContractLineItem]:
    """
    Send the raw PDF to Claude's vision API for direct document reading.
    Tries document type first, falls back to image-based page rendering.
    """
    # Try document-based approach first (requires anthropic SDK >= 0.40)
    items = _try_pdf_document_extraction(file_path, upload_id, org_id, db)
    if items:
        return items

    # Fall back to rendering pages as images
    print("Document-type extraction failed, trying image-based page rendering...")
    return _try_pdf_image_extraction(file_path, upload_id, org_id, db)


def _try_pdf_document_extraction(file_path: str, upload_id: str, org_id: int, db: Session) -> list[ContractLineItem]:
    """Send PDF as a document content block to Claude."""
    import anthropic

    try:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()

        if len(pdf_bytes) > 32 * 1024 * 1024:
            print(f"PDF too large for vision extraction: {len(pdf_bytes)} bytes")
            return []

        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        import time
        last_err = None
        for attempt in range(3):
            try:
                message = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=4096,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_b64,
                                },
                            },
                            {"type": "text", "text": _VISION_EXTRACTION_PROMPT},
                        ],
                    }],
                )
                break
            except Exception as api_err:
                last_err = api_err
                print(f"Document extraction attempt {attempt + 1} failed: {api_err}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
        else:
            print(f"Document extraction failed after 3 attempts: {last_err}")
            return []

        items = _parse_ai_response_to_items(
            message.content[0].text, upload_id, org_id, db, "pdf_vision"
        )
        print(f"Document extraction found {len(items)} line items")
        return items

    except Exception as e:
        import traceback
        print(f"Document-type PDF extraction error: {e}")
        traceback.print_exc()
        return []


def _try_pdf_image_extraction(file_path: str, upload_id: str, org_id: int, db: Session) -> list[ContractLineItem]:
    """Render PDF pages as images and send to Claude vision."""
    import anthropic

    try:
        import fitz  # PyMuPDF
    except ImportError:
        try:
            from pdf2image import convert_from_path
            return _try_pdf_image_extraction_pdf2image(file_path, upload_id, org_id, db)
        except ImportError:
            print("Neither PyMuPDF nor pdf2image available for image-based extraction")
            return _try_pdf_pdfplumber_image_extraction(file_path, upload_id, org_id, db)

    try:
        doc = fitz.open(file_path)
        page_indices = list(range(min(doc.page_count, 5)))

        if doc.page_count > 10:
            pages_data = extract_pages_from_pdf(file_path)
            if pages_data:
                scored = [(i, _score_page_for_pricing(p["text"])) for i, p in enumerate(pages_data)]
                scored.sort(key=lambda x: x[1], reverse=True)
                page_indices = sorted([idx for idx, _ in scored[:5]])

        image_blocks = []
        for page_num in page_indices:
            if page_num >= doc.page_count:
                continue
            page = doc[page_num]
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            img_b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
            image_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64,
                },
            })
        doc.close()

        if not image_blocks:
            return []

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        content = image_blocks + [{"type": "text", "text": _VISION_EXTRACTION_PROMPT}]

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )

        items = _parse_ai_response_to_items(
            message.content[0].text, upload_id, org_id, db, "pdf_vision"
        )
        print(f"Image extraction (PyMuPDF) found {len(items)} line items")
        return items

    except Exception as e:
        import traceback
        print(f"Image-based PDF extraction error: {e}")
        traceback.print_exc()
        return []


def _try_pdf_pdfplumber_image_extraction(file_path: str, upload_id: str, org_id: int, db: Session) -> list[ContractLineItem]:
    """Last resort: use pdfplumber to render page images."""
    import anthropic

    try:
        import pdfplumber
        from io import BytesIO

        image_blocks = []
        with pdfplumber.open(file_path) as pdf:
            page_indices = list(range(min(len(pdf.pages), 5)))

            if len(pdf.pages) > 10:
                pages_data = extract_pages_from_pdf(file_path)
                if pages_data:
                    scored = [(i, _score_page_for_pricing(p["text"])) for i, p in enumerate(pages_data)]
                    scored.sort(key=lambda x: x[1], reverse=True)
                    page_indices = sorted([idx for idx, _ in scored[:5]])

            for idx in page_indices:
                if idx >= len(pdf.pages):
                    continue
                page = pdf.pages[idx]
                img = page.to_image(resolution=200)
                buf = BytesIO()
                img.save(buf, format="PNG")
                img_b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
                image_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    },
                })

        if not image_blocks:
            return []

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        content = image_blocks + [{"type": "text", "text": _VISION_EXTRACTION_PROMPT}]

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": content}],
        )

        items = _parse_ai_response_to_items(
            message.content[0].text, upload_id, org_id, db, "pdf_vision"
        )
        print(f"Image extraction (pdfplumber) found {len(items)} line items")
        return items

    except Exception as e:
        import traceback
        print(f"Pdfplumber image extraction error: {e}")
        traceback.print_exc()
        return []


def _parse_ai_response_to_items(
    response_text: str, upload_id: str, org_id: int, db: Session, source: str
) -> list[ContractLineItem]:
    """Parse Claude's JSON response into ContractLineItem objects."""
    response_text = response_text.strip()

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
            extraction_source=source,
            extraction_confidence=0.85,
        )
        items.append(item)
    return items


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
