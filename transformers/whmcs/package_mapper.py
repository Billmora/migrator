import json
from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger
import re

logger = get_logger(__name__)

class PackageMapper(BaseMapper):
    
    def __init__(self, currency_mapper=None):
        self.currency_mapper = currency_mapper
        
        # Accumulator: (type, relid) -> dict of cycles -> dict of currency -> price data
        self.pricing_accumulator = {}
        
        # Lookup: (type, relid, cycle) -> package_price_id
        self.package_price_lookup = {}
        self.next_price_id = 1
        
        # Track which relids we have emitted in Pass 2 to avoid duplicates
        self.emitted_pricing = set()

    def _generate_slug(self, text: str) -> str:
        if not text:
            return "unknown-slug"
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'[\s-]+', '-', text).strip('-')
        return text

    def map_productgroups(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        catalog_id = self.safe_int(row.get("id"))
        if not catalog_id: return []

        name = row.get("name", f"Catalog {catalog_id}")
        headline = row.get("headline", "")
        slug_src = headline if headline else name
        is_hidden = self.safe_int(row.get("hidden", 0))
        
        catalog_dict = {
            "id": catalog_id,
            "name": name,
            "slug": self._generate_slug(slug_src),
            "description": row.get("tagline", "") or "",
            "icon": None,
            "status": "hidden" if is_hidden else "visible",
            "sort_order": self.safe_int(row.get("order", 0)),
            "created_at": self.map_date(row.get("created_at")),
            "updated_at": self.map_date(row.get("updated_at", row.get("created_at")))
        }
        return [("catalogs", catalog_dict)]

    def map_products(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        package_id = self.safe_int(row.get("id"))
        if not package_id: return []

        name = row.get("name", f"Package {package_id}")
        is_hidden = self.safe_int(row.get("hidden", 0))
        retired = self.safe_int(row.get("retired", 0))

        status = "visible"
        if is_hidden or retired:
            status = "hidden"

        qty = self.safe_int(row.get("qty", 0))
        stock_control = self.safe_int(row.get("stockcontrol", 0))
        stock = qty if stock_control else -1

        package_dict = {
            "id": package_id,
            "catalog_id": self.safe_int(row.get("gid", 0)),
            "name": name,
            "slug": self._generate_slug(name),
            "description": row.get("description", ""),
            "icon": None,
            "stock": stock,
            "per_user_limit": -1,
            "allow_cancellation": 1,
            "allow_quantity": "single",
            "status": status,
            "sort_order": self.safe_int(row.get("order", 0)),
            "plugin_id": None,
            "provisioning_config": None,
            "created_at": self.map_date(row.get("created_at")),
            "updated_at": self.map_date(row.get("updated_at", row.get("created_at")))
        }

        # If product is free or onetime, and has no pricing in tblpricing, we might need to emit a fallback price.
        # But for now, rely on tblpricing. If it's free, it usually has a tblpricing row with 0.00 or type='onetime'.

        return [("packages", package_dict)]

    def extract_pricing(self, row: Dict[str, Any]):
        """PASS 1: Accumulate pricing to group currencies."""
        ptype = row.get("type")
        if ptype not in ("product", "configoptions"):
            return
            
        relid = self.safe_int(row.get("relid"))
        if not relid: return
            
        currency_id = self.safe_int(row.get("currency", 1))
        currency_code = self.currency_mapper.get_code(currency_id) if self.currency_mapper else "USD"
        
        key = (ptype, relid)
        if key not in self.pricing_accumulator:
            self.pricing_accumulator[key] = {
                "monthly": {}, "quarterly": {}, "semiannually": {}, 
                "annually": {}, "biennially": {}, "triennially": {}
            }
            
        acc = self.pricing_accumulator[key]
        
        def add_rate(cycle, price_col, setup_col):
            price = self.safe_float(row.get(price_col, -1.0))
            setup = self.safe_float(row.get(setup_col, 0.0))
            if price >= 0:
                acc[cycle][currency_code] = {
                    "currency": currency_code,
                    "price": str(price),
                    "setup_fee": str(max(0.0, setup)),
                    "enabled": True
                }

        add_rate("monthly", "monthly", "msetupfee")
        add_rate("quarterly", "quarterly", "qsetupfee")
        add_rate("semiannually", "semiannually", "ssetupfee")
        add_rate("annually", "annually", "asetupfee")
        add_rate("biennially", "biennially", "bsetupfee")
        add_rate("triennially", "triennially", "tsetupfee")

        # Also allocate package_price_id for each valid cycle
        for cycle in acc.keys():
            if acc[cycle] and (ptype, relid, cycle) not in self.package_price_lookup:
                self.package_price_lookup[(ptype, relid, cycle)] = self.next_price_id
                self.next_price_id += 1

    def map_pricing(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """PASS 2: Emit the accumulated pricing."""
        ptype = row.get("type")
        if ptype != "product":
            return []

        relid = self.safe_int(row.get("relid"))
        if not relid: return []

        # Only emit once per product
        if relid in self.emitted_pricing:
            return []
        self.emitted_pricing.add(relid)

        acc = self.pricing_accumulator.get((ptype, relid))
        if not acc: return []

        results = []
        
        CYCLE_MAP = {
            "monthly": ("Monthly", 1, "monthly"),
            "quarterly": ("Quarterly", 3, "monthly"),
            "semiannually": ("Semi-Annually", 6, "monthly"),
            "annually": ("Annually", 1, "yearly"),
            "biennially": ("Biennially", 2, "yearly"),
            "triennially": ("Triennially", 3, "yearly"),
        }

        # Build full disabled rates template based on all known currencies
        known_currencies = set()
        for cycle_rates in acc.values():
            known_currencies.update(cycle_rates.keys())
        
        if self.currency_mapper:
            known_currencies.add(self.currency_mapper.get_default_code())

        for cycle, cycle_rates in acc.items():
            if not cycle_rates: continue # skip empty cycles

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

            price_id = self.package_price_lookup.get((ptype, relid, cycle))
            name, interval, period = CYCLE_MAP[cycle]

            is_free = True
            for cr in cycle_rates.values():
                if float(cr.get("price", 0)) > 0 or float(cr.get("setup_fee", 0)) > 0:
                    is_free = False
                    break

            if is_free:
                p_type = "free"
                name = "Free"
                for cur in rates_json:
                    rates_json[cur]["price"] = None
                    rates_json[cur]["setup_fee"] = None
            else:
                p_type = "recurring"

            price_dict = {
                "id": price_id,
                "package_id": relid,
                "name": name,
                "type": p_type,
                "time_interval": interval,
                "billing_period": period,
                "rates": rates_json,
                "created_at": None,
                "updated_at": None
            }
            results.append(("package_prices", price_dict))

        return results
