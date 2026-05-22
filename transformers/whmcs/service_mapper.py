from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class ServiceMapper(BaseMapper):

    def __init__(self, currency_mapper=None):
        self.currency_mapper = currency_mapper

    def map_hosting(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Maps WHMCS tblhosting to Billmora services.
        """
        service_id = self.safe_int(row.get("id"))
        if not service_id:
            return []

        user_id = self.safe_int(row.get("userid", 0))
        package_id = self.safe_int(row.get("packageid", 0))

        domain = row.get("domain", "")
        # If no domain, default to a generic name
        name = domain if domain else f"Service {service_id}"

        # Status mapping
        whmcs_status = str(row.get("domainstatus", "")).lower()
        # Billmora expects: pending, active, suspended, terminated, cancelled
        valid_statuses = {"pending", "active", "suspended", "terminated", "cancelled"}
        if whmcs_status not in valid_statuses:
            whmcs_status = "pending"

        # Billing cycle mapping
        whmcs_cycle = str(row.get("billingcycle", "")).lower()
        billing_type = "free"
        billing_interval = None
        billing_period = None

        if whmcs_cycle in ["one time", "onetime"]:
            billing_type = "onetime"
        elif whmcs_cycle == "monthly":
            billing_type = "recurring"
            billing_interval = 1
            billing_period = "monthly"
        elif whmcs_cycle == "quarterly":
            billing_type = "recurring"
            billing_interval = 3
            billing_period = "monthly"
        elif whmcs_cycle == "semi-annually":
            billing_type = "recurring"
            billing_interval = 6
            billing_period = "monthly"
        elif whmcs_cycle == "annually":
            billing_type = "recurring"
            billing_interval = 1
            billing_period = "yearly"
        elif whmcs_cycle == "biennially":
            billing_type = "recurring"
            billing_interval = 2
            billing_period = "yearly"
        elif whmcs_cycle == "triennially":
            billing_type = "recurring"
            billing_interval = 3
            billing_period = "yearly"

        # Note: Billmora schema requires order_id, package_price_id. 
        # FOREIGN_KEY_CHECKS=0 allows us to insert fallback values if strict matches aren't found.
        order_id = self.safe_int(row.get("orderid", 1))

        # Setup fee approx: WHMCS stores firstpaymentamount which is setup + recurring amount
        recurring_amount = self.safe_float(row.get("amount", 0.0))
        first_payment = self.safe_float(row.get("firstpaymentamount", 0.0))
        setup_fee = first_payment - recurring_amount
        if setup_fee < 0:
            setup_fee = 0.0

        service_dict = {
            "id": service_id,
            "service_number": f"SRV-W-{service_id}",
            "user_id": user_id,
            "order_id": order_id if order_id > 0 else 1,
            "order_item_id": None,
            "package_id": package_id if package_id > 0 else 1,
            "package_price_id": 1, # Fallback
            "plugin_id": None,
            "variant_selections": None,
            "name": name,
            "status": whmcs_status,
            "currency": self.currency_mapper.get_code(row.get("currency", "1")) if self.currency_mapper else "USD",
            "billing_type": billing_type,
            "billing_interval": billing_interval,
            "billing_period": billing_period,
            "price": recurring_amount,
            "setup_fee": setup_fee,
            "subscription_id": row.get("subscriptionid", None),
            "activated_at": self.map_date(row.get("regdate")),
            "next_due_date": self.map_date(row.get("nextduedate")),
            "suspended_at": None,
            "terminated_at": None,
            "cancelled_at": None,
            "configuration": None,
            "created_at": self.map_date(row.get("regdate")),
            "updated_at": self.map_date(row.get("updated_at", row.get("regdate")))
        }

        return [("services", service_dict)]
