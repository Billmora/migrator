from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class CouponMapper(BaseMapper):
    """
    Maps WHMCS tblpromotions to Billmora coupons.
    """

    def map_promotions(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        promo_id = self.safe_int(row.get("id"))
        if not promo_id:
            return []

        code = row.get("code", "")
        if not code:
            return []

        # Type mapping
        whmcs_type = str(row.get("type", "")).lower()
        if whmcs_type == "percentage":
            billmora_type = "percentage"
        else:
            billmora_type = "fixed_amount"

        value = self.safe_float(row.get("value", 0.0))

        # Billing cycles - WHMCS stores as comma-separated string
        cycles_str = row.get("cycles", "")
        billing_cycles = None
        if cycles_str:
            billing_cycles = [c.strip() for c in str(cycles_str).split(",") if c.strip()]

        max_uses = self.safe_int(row.get("maxuses", 0)) or None
        uses = self.safe_int(row.get("uses", 0))

        # Per-client limitation
        once_per_client = self.safe_int(row.get("onceperclient", 0))
        max_uses_per_user = 1 if once_per_client else None

        start_at = self.map_date(row.get("startdate"))
        expires_at = self.map_date(row.get("expirationdate"))

        coupon_dict = {
            "id": promo_id,
            "code": code,
            "type": billmora_type,
            "value": value,
            "billing_cycles": billing_cycles,  # Will be JSON-encoded
            "max_uses": max_uses,
            "max_uses_per_user": max_uses_per_user,
            "start_at": start_at,
            "expires_at": expires_at,
            "total_uses": uses,
            "created_at": start_at,
            "updated_at": start_at,
        }

        return [("coupons", coupon_dict)]
