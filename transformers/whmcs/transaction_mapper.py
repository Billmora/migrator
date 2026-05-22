from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class TransactionMapper(BaseMapper):
    """
    Maps WHMCS tblaccounts to Billmora transactions.
    """

    def __init__(self, currency_mapper=None):
        self.currency_mapper = currency_mapper

    def map_accounts(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        txn_id = self.safe_int(row.get("id"))
        if not txn_id:
            return []

        user_id = self.safe_int(row.get("userid", 0))
        invoice_id = self.safe_int(row.get("invoiceid", 0))

        # Skip if no invoice link (Billmora requires invoice_id FK)
        if not invoice_id:
            return []

        amount_in = self.safe_float(row.get("amountin", 0.0))
        amount_out = self.safe_float(row.get("amountout", 0.0))
        amount = amount_in - amount_out

        # Resolve currency
        currency_id = row.get("currency", "1")
        currency = "USD"
        if self.currency_mapper:
            currency = self.currency_mapper.get_code(currency_id)

        date = self.map_date(row.get("date"))

        txn_dict = {
            "id": txn_id,
            "user_id": user_id,
            "invoice_id": invoice_id,
            "plugin_id": None,
            "reference": row.get("transid", None) or None,
            "description": row.get("description", "Payment"),
            "currency": currency,
            "amount": amount,
            "fee": self.safe_float(row.get("fees", 0.0)),
            "created_at": date,
            "updated_at": date,
        }

        return [("transactions", txn_dict)]
