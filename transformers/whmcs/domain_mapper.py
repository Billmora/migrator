import json
from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class DomainMapper(BaseMapper):
    """
    Maps WHMCS tbldomains to Billmora registrants.
    Auto-creates Billmora tlds entries based on extracted domains.
    """

    def __init__(self, currency_mapper=None):
        self.currency_mapper = currency_mapper
        self.tld_map = {} # string -> int
        self.next_tld_id = 1

    def map_domains(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        domain_id = self.safe_int(row.get("id"))
        if not domain_id:
            return []

        user_id = self.safe_int(row.get("userid", 0))
        domain = row.get("domain", "")
        if not domain:
            return []

        results = []

        # Extract TLD
        parts = domain.split(".")
        if len(parts) > 1:
            # handle cases like .co.uk or .com
            # To keep it simple, we just take the last part. Or last two if .co.uk?
            # A common approach is to split on first dot.
            tld_str = domain.split(".", 1)[1].lower()
        else:
            tld_str = "com"

        if tld_str not in self.tld_map:
            tld_id = self.next_tld_id
            self.tld_map[tld_str] = tld_id
            self.next_tld_id += 1
            
            tlds_dict = {
                "id": tld_id,
                "tld": tld_str,
                "plugin_id": None, # Will need manual configuration later
                "min_years": 1,
                "max_years": 10,
                "grace_period_days": 0,
                "redemption_period_days": 0,
                "whois_privacy": 0,
                "status": "visible",
                "sort_order": 0,
                "created_at": None,
                "updated_at": None
            }
            results.append(("tlds", tlds_dict))
        else:
            tld_id = self.tld_map[tld_str]

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
        currency = self.currency_mapper.get_default_code() if self.currency_mapper else "USD"

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
            "tld_id": tld_id,
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

        results.append(("registrants", registrant_dict))
        return results
