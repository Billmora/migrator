from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class OrderMapper(BaseMapper):
    """
    Maps WHMCS tblorders to Billmora orders.
    """

    def __init__(self, currency_mapper=None):
        self.currency_mapper = currency_mapper

    def map_orders(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        order_id = self.safe_int(row.get("id"))
        if not order_id:
            return []

        user_id = self.safe_int(row.get("userid", 0))
        order_num = row.get("ordernum", "")
        if not order_num:
            order_num = f"ORD-W-{order_id}"

        # Status mapping
        whmcs_status = str(row.get("status", "")).lower()
        status_map = {
            "pending": "pending",
            "active": "completed",
            "completed": "completed",
            "fraud": "cancelled",
            "cancelled": "cancelled",
        }
        billmora_status = status_map.get(whmcs_status, "pending")

        amount = self.safe_float(row.get("amount", 0.0))
        date = self.map_date(row.get("date"))

        currency = self.currency_mapper.get_default_code() if self.currency_mapper else "USD"

        completed_at = date if billmora_status == "completed" else None
        cancelled_at = date if billmora_status == "cancelled" else None

        order_dict = {
            "id": order_id,
            "user_id": user_id,
            "order_number": order_num,
            "status": billmora_status,
            "currency": currency,
            "subtotal": amount,
            "discount": 0.00,
            "setup_fee": 0.00,
            "tax": 0.00,
            "total": amount,
            "coupon_id": None,
            "notes": row.get("notes", None),
            "terms_accepted": 1,
            "completed_at": completed_at,
            "cancelled_at": cancelled_at,
            "created_at": date,
            "updated_at": date,
        }

        return [("orders", order_dict)]
