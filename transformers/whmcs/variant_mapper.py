from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger
import re

logger = get_logger(__name__)

class VariantMapper(BaseMapper):
    
    def __init__(self, package_mapper=None):
        self.package_mapper = package_mapper
        
        # Lookups built in Pass 1
        self.gid_to_variants = {} # gid -> list of variant_id
        self.gid_descriptions = {} # gid -> description
        
        # Track emissions in Pass 2 to avoid duplicate pricing
        self.emitted_variant_pricing = set()

    def _generate_slug(self, text: str) -> str:
        if not text:
            return "unknown-slug"
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'[\s-]+', '-', text).strip('-')
        return text

    def extract_configgroups(self, row: Dict[str, Any]):
        """Pass 1: Accumulate group names to use as descriptions."""
        gid = self.safe_int(row.get("id"))
        group_name = row.get("name", "")
        if gid:
            self.gid_descriptions[gid] = group_name

    def extract_configoptions(self, row: Dict[str, Any]):
        """Pass 1: Accumulate gid to variant_id mapping."""
        variant_id = self.safe_int(row.get("id"))
        gid = self.safe_int(row.get("gid"))
        if variant_id and gid:
            if gid not in self.gid_to_variants:
                self.gid_to_variants[gid] = []
            self.gid_to_variants[gid].append(variant_id)

    def map_productconfigoptions(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Pass 2: tblproductconfigoptions -> variants"""
        variant_id = self.safe_int(row.get("id"))
        if not variant_id: return []

        raw_name = str(row.get("optionname", f"Variant {variant_id}"))
        
        parts = raw_name.split("|", 1)
        if len(parts) == 2:
            code = parts[0].strip()
            name = parts[1].strip()
        else:
            name = raw_name.strip()
            code = self._generate_slug(name)
        
        # WHMCS optiontype: 1=Dropdown, 2=Radio, 3=Yes/No, 4=Quantity
        wtype = self.safe_int(row.get("optiontype", 1))
        type_map = {
            1: "select",
            2: "radio",
            3: "checkbox",
            4: "slider"
        }
        vtype = type_map.get(wtype, "select")

        # The code is already resolved via the pipe parsing above

        is_hidden = self.safe_int(row.get("hidden", 0))
        gid = self.safe_int(row.get("gid"))

        variant_dict = {
            "id": variant_id,
            "name": name,
            "description": self.gid_descriptions.get(gid),
            "type": vtype,
            "code": code,
            "status": "hidden" if is_hidden else "visible",
            "sort_order": self.safe_int(row.get("order", 0)),
            "is_scalable": 1 if vtype in ("select", "quantity") else 0,
            "created_at": None,
            "updated_at": None
        }

        return [("variants", variant_dict)]

    def map_productconfigoptionssub(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Pass 2: tblproductconfigoptionssub -> variant_options AND variant_prices"""
        sub_id = self.safe_int(row.get("id"))
        variant_id = self.safe_int(row.get("configid"))
        if not sub_id or not variant_id: return []

        raw_name = str(row.get("optionname", ""))
        
        # In WHMCS, optionname is often "Code|Friendly Name"
        parts = raw_name.split("|", 1)
        if len(parts) == 2:
            value = parts[0].strip()
            name = parts[1].strip()
        else:
            name = raw_name.strip()
            # If no pipe, the value in provisioning is sometimes the name or the id itself.
            # We will use the slugified name as a safe fallback value.
            value = self._generate_slug(name)

        is_hidden = self.safe_int(row.get("hidden", 0))

        variant_option_dict = {
            "id": sub_id,
            "variant_id": variant_id,
            "name": name,
            "value": value,
            "created_at": None,
            "updated_at": None
        }

        results = [("variant_options", variant_option_dict)]

        # Now handle pricing for this option
        # We rely on PackageMapper's pricing accumulator for type="configoptions", relid=sub_id
        if self.package_mapper:
            pm = self.package_mapper
            
            # Ensure we only emit pricing once per sub_id
            if sub_id not in self.emitted_variant_pricing:
                self.emitted_variant_pricing.add(sub_id)
                
                acc = pm.pricing_accumulator.get(("configoptions", sub_id))
                if acc:
                    CYCLE_MAP = {
                        "monthly": ("Monthly", 1, "monthly"),
                        "quarterly": ("Quarterly", 3, "monthly"),
                        "semiannually": ("Semi-Annually", 6, "monthly"),
                        "annually": ("Annually", 1, "yearly"),
                        "biennially": ("Biennially", 2, "yearly"),
                        "triennially": ("Triennially", 3, "yearly"),
                    }
                    
                    known_currencies = set()
                    for cycle_rates in acc.values():
                        known_currencies.update(cycle_rates.keys())
                    if pm.currency_mapper:
                        known_currencies.add(pm.currency_mapper.get_default_code())

                    for cycle, cycle_rates in acc.items():
                        if not cycle_rates: continue
                        
                        rates_json = {}
                        for cur in known_currencies:
                            if cur in cycle_rates:
                                rates_json[cur] = cycle_rates[cur]
                            else:
                                rates_json[cur] = {
                                    "currency": cur,
                                    "price": None,
                                    "setup_fee": None,
                                    "enabled": False
                                }
                        
                        price_id = pm.package_price_lookup.get(("configoptions", sub_id, cycle))
                        cycle_name, interval, period = CYCLE_MAP[cycle]

                        is_free = True
                        for cr in cycle_rates.values():
                            if float(cr.get("price", 0)) > 0 or float(cr.get("setup_fee", 0)) > 0:
                                is_free = False
                                break

                        if is_free:
                            p_type = "free"
                            cycle_name = "Free"
                            for cur in rates_json:
                                rates_json[cur]["price"] = None
                                rates_json[cur]["setup_fee"] = None
                        else:
                            p_type = "recurring"

                        price_dict = {
                            "id": price_id,
                            "variant_option_id": sub_id,
                            "name": cycle_name,
                            "type": p_type,
                            "time_interval": interval,
                            "billing_period": period,
                            "rates": rates_json,
                            "created_at": None,
                            "updated_at": None
                        }
                        results.append(("variant_prices", price_dict))

        return results

    def map_productconfiglinks(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Pass 2: tblproductconfiglinks -> package_variant"""
        pid = self.safe_int(row.get("pid"))
        gid = self.safe_int(row.get("gid"))
        
        if not pid or not gid: return []

        variant_ids = self.gid_to_variants.get(gid, [])
        results = []
        
        for vid in variant_ids:
            package_variant_dict = {
                "package_id": pid,
                "variant_id": vid,
                "created_at": None,
                "updated_at": None
            }
            results.append(("package_variant", package_variant_dict))
            
        return results
