from abc import ABC
from typing import Dict, Any, List, Tuple

class BaseMapper(ABC):
    """
    Abstract Base Class for all mappers.
    A mapper takes a source dictionary and returns a list of target tuples.
    Each tuple is (target_table_name, target_dictionary).
    """

    @staticmethod
    def map_date(date_str: Any) -> Any:
        """
        Safely maps zero-dates or empty dates to None.
        """
        if not date_str:
            return None
        if isinstance(date_str, str) and date_str.startswith("0000-00-00"):
            return None
        return date_str

    @staticmethod
    def safe_int(val: Any, default: int = 0) -> int:
        """
        Safely cast to int.
        """
        if val is None:
            return default
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_float(val: Any, default: float = 0.0) -> float:
        """
        Safely cast to float.
        """
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default
