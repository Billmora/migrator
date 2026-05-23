from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class CancellationMapper(BaseMapper):
    """
    Maps WHMCS tblcancelrequests to Billmora service_cancellations.
    """

    def __init__(self, service_mapper=None):
        self.service_mapper = service_mapper

    def map_cancel_requests(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        cancel_id = self.safe_int(row.get("id"))
        if not cancel_id:
            return []

        service_id = self.safe_int(row.get("relid", 0))
        if not service_id:
            return []

        # Type mapping
        whmcs_type = str(row.get("type", "")).lower()
        if "immediate" in whmcs_type:
            cancel_type = "immediate"
        else:
            cancel_type = "end_of_period"

        date = self.map_date(row.get("date")) or self.map_date(row.get("created_at"))
        
        user_id = 1
        if self.service_mapper:
            user_id = self.service_mapper.hosting_to_user_id.get(service_id, 1)

        cancel_dict = {
            "id": cancel_id,
            "service_id": service_id,
            "user_id": user_id,  # Resolved from tblhosting
            "reviewed_by": None,
            "status": "pending",
            "type": cancel_type,
            "reason": row.get("reason", ""),
            "rejection_note": None,
            "reviewed_at": None,
            "cancelled_at": None,
            "created_at": date,
            "updated_at": self.map_date(row.get("updated_at", date)),
        }

        return [("service_cancellations", cancel_dict)]
