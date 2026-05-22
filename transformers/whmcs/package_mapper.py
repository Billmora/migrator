import json
from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger
import re

logger = get_logger(__name__)

class PackageMapper(BaseMapper):
    
    def __init__(self):
        pass

    def _generate_slug(self, text: str) -> str:
        """
        Generates a basic URL-friendly slug.
        """
        if not text:
            return "unknown-slug"
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'[\s-]+', '-', text).strip('-')
        return text

    def map_productgroups(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Maps WHMCS tblproductgroups to Billmora catalogs.
        """
        catalog_id = self.safe_int(row.get("id"))
        if not catalog_id:
            return []

        name = row.get("name", f"Catalog {catalog_id}")
        # WHMCS doesn't strictly have a slug, we generate one from the name or headline
        headline = row.get("headline", "")
        slug_src = headline if headline else name
        
        is_hidden = self.safe_int(row.get("hidden", 0))
        
        catalog_dict = {
            "id": catalog_id,
            "name": name,
            "slug": self._generate_slug(slug_src) + f"-{catalog_id}",
            "description": row.get("tagline", "") or "",
            "icon": None,
            "status": "hidden" if is_hidden else "visible",
            "sort_order": self.safe_int(row.get("order", 0)),
            "created_at": self.map_date(row.get("created_at")),
            "updated_at": self.map_date(row.get("updated_at"))
        }

        return [("catalogs", catalog_dict)]

    def map_products(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Maps WHMCS tblproducts to Billmora packages.
        """
        package_id = self.safe_int(row.get("id"))
        if not package_id:
            return []

        name = row.get("name", f"Package {package_id}")
        is_hidden = self.safe_int(row.get("hidden", 0))
        retired = self.safe_int(row.get("retired", 0))

        # Determine status
        status = "visible"
        if is_hidden or retired:
            status = "hidden"

        # Stock control in WHMCS
        qty = self.safe_int(row.get("qty", 0))
        stock_control = self.safe_int(row.get("stockcontrol", 0))
        stock = qty if stock_control else -1

        package_dict = {
            "id": package_id,
            "catalog_id": self.safe_int(row.get("gid", 0)),
            "name": name,
            "slug": self._generate_slug(name) + f"-{package_id}",
            "description": row.get("description", ""),
            "icon": None,
            "stock": stock,
            "per_user_limit": -1,
            "allow_cancellation": 1,
            "allow_quantity": "single", # WHMCS defaults
            "status": status,
            "sort_order": self.safe_int(row.get("order", 0)),
            "plugin_id": None, # Requires module mapping later
            "provisioning_config": None,
            "created_at": self.map_date(row.get("created_at")),
            "updated_at": self.map_date(row.get("updated_at"))
        }

        return [("packages", package_dict)]

    def map_pricing(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Maps WHMCS tblpricing to Billmora package_prices (rates column).
        """
        # We only map product pricing (type = 'product')
        # Billmora uses package_prices which has a JSON rates column.
        if row.get("type") != "product":
            return []

        relid = self.safe_int(row.get("relid"))
        if not relid:
            return []

        # Parse WHMCS pricing matrix
        rates = {}
        
        # Helper to safely add to rates if not -1
        def add_rate(period: str, price_col: str, setup_col: str):
            price = self.safe_float(row.get(price_col, -1.0))
            setup = self.safe_float(row.get(setup_col, 0.0))
            if price >= 0:
                rates[period] = {
                    "setup": max(0.0, setup),
                    "price": price
                }

        add_rate("monthly", "monthly", "msetupfee")
        add_rate("quarterly", "quarterly", "qsetupfee")
        add_rate("semi-annually", "semiannually", "ssetupfee")
        add_rate("annually", "annually", "asetupfee")
        add_rate("biennially", "biennially", "bsetupfee")
        add_rate("triennially", "triennially", "tsetupfee")

        if not rates:
            return []

        # We don't have a specific ID for package_prices, we map directly to the package
        # but we need to generate an ID or let MySQL auto-increment if we don't supply one.
        # But wait, without an ID, we can't link variants. Fortunately, we aren't doing variants right now.
        
        # We will let MySQL auto-increment the ID by not providing it
        price_dict = {
            "package_id": relid,
            "name": "Default Pricing",
            "type": "recurring",
            "time_interval": None,
            "billing_period": None,
            "rates": rates, # Dict will be JSON-encoded by SQLGenerator
            "created_at": None,
            "updated_at": None
        }

        return [("package_prices", price_dict)]
