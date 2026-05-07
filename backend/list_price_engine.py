from __future__ import annotations

"""
List-price lookup and discount calculation for contract line items.

Matching priority:
  1. SKU / manufacturer part number (exact)
  2. Canonical product name — prefer 1-year term, take max annual price
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import ContractLineItem, ListPrice, PriceList


def get_list_price_for_item(item: ContractLineItem, db: Session) -> dict:
    """
    Find the applicable list price and compute discount for a line item.

    Returns dict with:
      list_price_annual, discount_pct, discount_amount_annual, list_price_source
    """
    result = {
        "list_price_annual": None,
        "discount_pct": None,
        "discount_amount_annual": None,
        "list_price_source": None,
    }

    active_list_ids = db.query(PriceList.id).filter(
        PriceList.vendor_name == item.vendor_name,
        PriceList.is_active == True,
    ).scalar_subquery()

    # 1. Try SKU match
    if item.sku:
        sku_match = db.query(ListPrice.list_price_annual_usd).filter(
            ListPrice.price_list_id.in_(active_list_ids),
            ListPrice.manufacturer_part_number == item.sku,
            ListPrice.list_price_annual_usd > 0,
        ).first()
        if sku_match:
            return _compute_discount(item, sku_match[0], "sku_match")

    # 2. Canonical name match — prefer 1-year rows, take max price
    one_year = db.query(func.max(ListPrice.list_price_annual_usd)).filter(
        ListPrice.price_list_id.in_(active_list_ids),
        ListPrice.product_name_canonical == item.product_name,
        ListPrice.list_price_annual_usd > 0,
        ListPrice.duration_years == 1.0,
    ).scalar()

    if one_year and one_year > 0:
        return _compute_discount(item, one_year, "canonical_1yr")

    # 3. Any duration, annualized
    any_duration = db.query(func.max(ListPrice.list_price_annual_usd)).filter(
        ListPrice.price_list_id.in_(active_list_ids),
        ListPrice.product_name_canonical == item.product_name,
        ListPrice.list_price_annual_usd > 0,
    ).scalar()

    if any_duration and any_duration > 0:
        return _compute_discount(item, any_duration, "canonical_annualized")

    return result


def _compute_discount(item: ContractLineItem, list_price_annual: float, source: str) -> dict:
    cost = item.cost_per_unit_annual or 0.0
    if list_price_annual <= 0:
        return {
            "list_price_annual": round(list_price_annual, 2),
            "discount_pct": None,
            "discount_amount_annual": None,
            "list_price_source": source,
        }

    discount_pct = ((list_price_annual - cost) / list_price_annual) * 100
    discount_amount = (list_price_annual - cost) * (item.quantity or 1)

    return {
        "list_price_annual": round(list_price_annual, 2),
        "discount_pct": round(discount_pct, 1),
        "discount_amount_annual": round(discount_amount, 2),
        "list_price_source": source,
    }
