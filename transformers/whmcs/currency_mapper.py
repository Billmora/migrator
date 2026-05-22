from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class CurrencyMapper(BaseMapper):
    """
    Maps WHMCS tblcurrencies to Billmora currencies.
    Also builds a lookup dict (id -> code) for other mappers to use.
    """

    def __init__(self):
        self.id_to_code: Dict[int, str] = {}

    def map_currencies(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        currency_id = self.safe_int(row.get("id"))
        if not currency_id:
            return []

        code = str(row.get("code", "USD")).upper().strip()
        
        # Store for lookup by other mappers
        self.id_to_code[currency_id] = code

        # WHMCS format values: 1 = 1,234.56 | 2 = 1.234,56 | 3 = 1234.56 | 4 = 1,234
        whmcs_format = self.safe_int(row.get("format", 1))
        format_map = {
            1: "1,234.56",
            2: "1.234,56",
            3: "1234.56",
            4: "1,234",
        }
        billmora_format = format_map.get(whmcs_format, "1234.56")

        is_default = 1 if str(row.get("default", "0")) == "1" else 0

        currency_dict = {
            "id": currency_id,
            "code": code,
            "prefix": row.get("prefix", ""),
            "suffix": row.get("suffix", ""),
            "format": billmora_format,
            "base_rate": self.safe_float(row.get("rate", 1.0)),
            "is_default": is_default,
            "created_at": None,
            "updated_at": None,
        }

        return [("currencies", currency_dict)]

    def get_code(self, currency_id: Any) -> str:
        """Lookup currency code by WHMCS currency ID."""
        cid = self.safe_int(currency_id, default=0)
        return self.id_to_code.get(cid, "USD")
