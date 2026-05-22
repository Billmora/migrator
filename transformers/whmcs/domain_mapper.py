from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class DomainMapper(BaseMapper):
    """
    Maps WHMCS tbldomains to Billmora registrants.
    """

    def __init__(self, currency_mapper=None):
        self.currency_mapper = currency_mapper

    def map_domains(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        domain_id = self.safe_int(row.get("id"))
        if not domain_id:
            return []

        user_id = self.safe_int(row.get("userid", 0))
        domain = row.get("domain", "")
        if not domain:
            return []

        # Status mapping
        whmcs_status = str(row.get("status", "")).lower()
        status_map = {
            "active": "active",
            "pending": "pending",
            "pending transfer": "pending_transfer",
            "expired": "expired",
            "cancelled": "cancelled",
            "transferred away": "transferred_away",
            "fraud": "cancelled",
            "redemption": "redemption",
        }
        billmora_status = status_map.get(whmcs_status, "pending")

        # Registration type
        whmcs_type = str(row.get("type", "Register")).lower()
        reg_type = "transfer" if "transfer" in whmcs_type else "register"

        # Currency fallback
        currency = "USD"
        if self.currency_mapper and self.currency_mapper.id_to_code:
            # Use default currency
            for cid, code in self.currency_mapper.id_to_code.items():
                currency = code
                break

        order_id = self.safe_int(row.get("orderid", 0)) or None
        auto_renew = 0 if self.safe_int(row.get("donotrenew", 0)) else 1

        reg_date = self.map_date(row.get("registrationdate"))
        expiry_date = self.map_date(row.get("expirydate"))

        registrant_dict = {
            "id": domain_id,
            "registrant_number": f"DOM-W-{domain_id}",
            "user_id": user_id,
            "order_id": order_id,
            "order_item_id": None,
            "tld_id": 1,  # Fallback, TLDs are configured fresh in Billmora
            "plugin_id": None,
            "domain": domain,
            "status": billmora_status,
            "registration_type": reg_type,
            "years": self.safe_int(row.get("registrationperiod", 1)),
            "currency": currency,
            "price": self.safe_float(row.get("recurringamount", 0.0)),
            "auto_renew": auto_renew,
            "nameservers": None,
            "configuration": None,
            "registered_at": reg_date,
            "expires_at": expiry_date,
            "suspended_at": None,
            "cancelled_at": None,
            "created_at": self.map_date(row.get("created_at", reg_date)),
            "updated_at": self.map_date(row.get("updated_at", reg_date)),
        }

        return [("registrants", registrant_dict)]
