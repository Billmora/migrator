import json
from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class ServiceMapper(BaseMapper):

    def __init__(self, currency_mapper=None, package_mapper=None, variant_mapper=None, plugin_mapper=None):
        self.currency_mapper = currency_mapper
        self.package_mapper = package_mapper
        self.variant_mapper = variant_mapper
        self.plugin_mapper = plugin_mapper
        
        self.hosting_to_user_id = {}
        self.hosting_variant_selections = {} # hosting_id -> dict of variant_id -> [variant_option_id]

    def extract_hosting(self, row: Dict[str, Any]):
        """Pass 1: Build lookup for Cancel/Ticket Mappers"""
        hid = self.safe_int(row.get("id"))
        uid = self.safe_int(row.get("userid"))
        if hid and uid:
            self.hosting_to_user_id[hid] = uid

    def extract_hostingconfigoptions(self, row: Dict[str, Any]):
        """Pass 1: Accumulate variant selections"""
        relid = self.safe_int(row.get("relid")) # hosting_id
        configid = self.safe_int(row.get("configid")) # variant_id in WHMCS?
        # Wait, in WHMCS, configid is the gid (tblproductconfigoptions.id)
        # optionid is the selected sub-option (tblproductconfigoptionssub.id)
        optionid = self.safe_int(row.get("optionid"))
        qty = self.safe_int(row.get("qty", 0))
        
        if not relid or not configid: return
        
        if relid not in self.hosting_variant_selections:
            self.hosting_variant_selections[relid] = {}
            
        str_configid = str(configid)
        if str_configid not in self.hosting_variant_selections[relid]:
            self.hosting_variant_selections[relid][str_configid] = []
            
        # For quantity type, WHMCS uses qty column
        # If optionid exists, append it
        if optionid:
            self.hosting_variant_selections[relid][str_configid].append(optionid)
        elif qty > 0:
            # If no optionid but qty is set, maybe it's a quantity variant?
            # Billmora variants have no dedicated qty value inside the array, they just use variant_option_id.
            # But let's append what we have.
            pass

    def map_hosting(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Pass 2: Maps WHMCS tblhosting to Billmora services."""
        service_id = self.safe_int(row.get("id"))
        if not service_id: return []

        user_id = self.safe_int(row.get("userid", 0))
        package_id = self.safe_int(row.get("packageid", 0))

        domain = row.get("domain", "")
        name = domain if domain else f"Service {service_id}"

        whmcs_status = str(row.get("domainstatus", "")).lower()
        valid_statuses = {"pending", "active", "suspended", "terminated", "cancelled"}
        if whmcs_status not in valid_statuses:
            whmcs_status = "pending"

        whmcs_cycle = str(row.get("billingcycle", "")).lower()
        billing_type = "free"
        billing_interval = None
        billing_period = None
        cycle_key = None

        if whmcs_cycle in ["one time", "onetime"]:
            billing_type = "onetime"
            cycle_key = "monthly"
        elif whmcs_cycle in ["free account", "free"]:
            billing_type = "free"
            cycle_key = "monthly"
        elif whmcs_cycle == "monthly":
            billing_type = "recurring"
            billing_interval = 1
            billing_period = "monthly"
            cycle_key = "monthly"
        elif whmcs_cycle == "quarterly":
            billing_type = "recurring"
            billing_interval = 3
            billing_period = "monthly"
            cycle_key = "quarterly"
        elif whmcs_cycle == "semi-annually":
            billing_type = "recurring"
            billing_interval = 6
            billing_period = "monthly"
            cycle_key = "semiannually"
        elif whmcs_cycle == "annually":
            billing_type = "recurring"
            billing_interval = 1
            billing_period = "yearly"
            cycle_key = "annually"
        elif whmcs_cycle == "biennially":
            billing_type = "recurring"
            billing_interval = 2
            billing_period = "yearly"
            cycle_key = "biennially"
        elif whmcs_cycle == "triennially":
            billing_type = "recurring"
            billing_interval = 3
            billing_period = "yearly"
            cycle_key = "triennially"

        order_id = self.safe_int(row.get("orderid", 1))

        recurring_amount = self.safe_float(row.get("amount", 0.0))
        first_payment = self.safe_float(row.get("firstpaymentamount", 0.0))
        setup_fee = max(0.0, first_payment - recurring_amount)

        # Lookup package_price_id
        package_price_id = 1
        if self.package_mapper and cycle_key:
            lookup = self.package_mapper.package_price_lookup.get(("product", package_id, cycle_key))
            if lookup:
                package_price_id = lookup

        # Build variant_selections JSON
        variant_selections = None
        sel = self.hosting_variant_selections.get(service_id)
        if sel:
            variant_selections = json.dumps(sel)

        # Build configuration JSON (provisioning data)
        config_data = {}
        for key in ["username", "password", "dedicatedip", "assignedips", "ns1", "ns2"]:
            val = row.get(key)
            if val: config_data[key] = val
            
        configuration = json.dumps(config_data) if config_data else None

        # Timestamps
        created_at = self.map_date(row.get("regdate"))
        updated_at = self.map_date(row.get("updated_at", created_at))
        suspended_at = self.map_date(row.get("overidesuspenduntil")) if whmcs_status == "suspended" else None
        
        # Handle termination/cancellation dates
        termination_date = self.map_date(row.get("termination_date"))
        terminated_at = termination_date if whmcs_status == "terminated" else None
        cancelled_at = termination_date if whmcs_status == "cancelled" else None

        service_dict = {
            "id": service_id,
            "service_number": f"SRV-W-{service_id}",
            "user_id": user_id,
            "order_id": order_id if order_id > 0 else 1,
            "order_item_id": None,
            "package_id": package_id if package_id > 0 else 1,
            "package_price_id": package_price_id,
            "plugin_id": None, # Services inherit provisioning logic from their package in Billmora
            "variant_selections": variant_selections,
            "name": name,
            "status": whmcs_status,
            "currency": self.currency_mapper.get_default_code() if self.currency_mapper else "USD",
            "billing_type": billing_type,
            "billing_interval": billing_interval,
            "billing_period": billing_period,
            "price": recurring_amount,
            "setup_fee": setup_fee,
            "subscription_id": row.get("subscriptionid", None),
            "activated_at": created_at,
            "next_due_date": self.map_date(row.get("nextduedate")),
            "suspended_at": suspended_at,
            "terminated_at": terminated_at,
            "cancelled_at": cancelled_at,
            "configuration": configuration,
            "fields": None,
            "admin_notes": None,
            "created_at": created_at,
            "updated_at": updated_at
        }

        return [("services", service_dict)]
