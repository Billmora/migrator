from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class InvoiceMapper(BaseMapper):

    def __init__(self, currency_mapper=None):
        self.currency_mapper = currency_mapper

    def map_invoices(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Maps WHMCS tblinvoices to Billmora invoices.
        """
        invoice_id = self.safe_int(row.get("id"))
        if not invoice_id:
            return []

        user_id = self.safe_int(row.get("userid", 0))
        
        invoicenum = row.get("invoicenum", "")
        if not invoicenum:
            invoicenum = f"INV-{invoice_id}"

        # Status mapping
        whmcs_status = str(row.get("status", "")).lower()
        valid_statuses = {"unpaid", "paid", "cancelled", "refunded"}
        
        if whmcs_status not in valid_statuses:
            whmcs_status = "unpaid"

        # Handle dates
        created_at = self.map_date(row.get("date"))
        due_date = self.map_date(row.get("duedate")) or created_at
        paid_at = self.map_date(row.get("datepaid"))

        if whmcs_status == "unpaid":
            paid_at = None

        invoice_dict = {
            "id": invoice_id,
            "user_id": user_id,
            "order_id": None, # WHMCS usually links orders -> invoices, not stored purely on invoice table
            "plugin_id": None,
            "invoice_number": invoicenum,
            "status": whmcs_status,
            "currency": self.currency_mapper.get_default_code() if self.currency_mapper else "USD",
            "subtotal": self.safe_float(row.get("subtotal", 0.0)),
            "discount": self.safe_float(row.get("credit", 0.0)),
            "tax": self.safe_float(row.get("tax", 0.0)) + self.safe_float(row.get("tax2", 0.0)),
            "total": self.safe_float(row.get("total", 0.0)),
            "due_date": due_date,
            "paid_at": paid_at,
            "created_at": created_at,
            "updated_at": self.map_date(row.get("updated_at", created_at))
        }

        return [("invoices", invoice_dict)]

    def map_invoice_items(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Maps WHMCS tblinvoiceitems to Billmora invoice_items.
        """
        item_id = self.safe_int(row.get("id"))
        if not item_id:
            return []

        invoice_id = self.safe_int(row.get("invoiceid", 0))
        
        # In WHMCS, type='Hosting' and relid points to tblhosting
        whmcs_type = str(row.get("type", "")).lower()
        relid = self.safe_int(row.get("relid", 0))
        
        service_id = relid if whmcs_type == "hosting" and relid > 0 else None
        registrant_id = relid if whmcs_type == "domainregister" and relid > 0 else None

        amount = self.safe_float(row.get("amount", 0.0))

        item_dict = {
            "id": item_id,
            "invoice_id": invoice_id,
            "service_id": service_id,
            "registrant_id": registrant_id,
            "description": row.get("description", "Invoice Item"),
            "quantity": 1, # WHMCS items are usually qty 1
            "unit_price": amount,
            "amount": amount,
            "created_at": self.map_date(row.get("created_at")), # Usually doesn't have created_at, we can leave None
            "updated_at": self.map_date(row.get("updated_at"))
        }

        return [("invoice_items", item_dict)]
