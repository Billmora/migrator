from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class TicketMapper(BaseMapper):
    """
    Maps WHMCS tbltickets and tblticketreplies to Billmora tickets and ticket_messages.
    """

    def __init__(self):
        self.dept_map: Dict[int, str] = {}

    def map_departments(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Builds department lookup (does not produce output rows).
        """
        dept_id = self.safe_int(row.get("id"))
        name = row.get("name", "")
        if dept_id and name:
            self.dept_map[dept_id] = name
        return []

    def map_tickets(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        ticket_id = self.safe_int(row.get("id"))
        if not ticket_id:
            return []

        user_id = self.safe_int(row.get("userid", 0))
        tid = row.get("tid", f"TKT-{ticket_id}")

        # Status mapping
        whmcs_status = str(row.get("status", "")).lower()
        status_map = {
            "open": "open",
            "answered": "answered",
            "customer-reply": "replied",
            "closed": "closed",
            "on hold": "on_hold",
            "in progress": "in_progress",
        }
        billmora_status = status_map.get(whmcs_status, "open")

        # Priority mapping
        whmcs_urgency = str(row.get("urgency", "")).lower()
        priority_map = {
            "low": "low",
            "medium": "medium",
            "high": "high",
        }
        billmora_priority = priority_map.get(whmcs_urgency, "normal")

        # Department
        dept_id = self.safe_int(row.get("did", 0))
        department = self.dept_map.get(dept_id, None)

        # Service link
        service_str = row.get("service", "")
        service_id = None
        if service_str:
            # WHMCS stores as "S123" format
            try:
                if service_str.startswith("S"):
                    service_id = int(service_str[1:])
            except (ValueError, TypeError):
                pass

        date = self.map_date(row.get("date"))
        last_reply = self.map_date(row.get("lastreply"))
        closed_at = None
        if billmora_status == "closed":
            closed_at = last_reply or date

        results = []

        ticket_dict = {
            "id": ticket_id,
            "ticket_number": str(tid),
            "subject": row.get("title", "No Subject"),
            "status": billmora_status,
            "priority": billmora_priority,
            "department": department,
            "user_id": user_id,
            "assigned_to": None,
            "service_id": service_id,
            "last_reply_at": last_reply,
            "closed_at": closed_at,
            "created_at": date,
            "updated_at": self.map_date(row.get("updated_at")) or date,
        }
        results.append(("tickets", ticket_dict))

        # The initial message from tbltickets.message becomes the first ticket_message
        message = row.get("message", "")
        if message:
            msg_dict = {
                "ticket_id": ticket_id,
                "user_id": user_id if user_id > 0 else 1,
                "message": message,
                "is_staff_reply": 0,
                "created_at": date,
                "updated_at": self.map_date(row.get("updated_at")) or date,
            }
            results.append(("ticket_messages", msg_dict))

        return results

    def map_replies(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        reply_id = self.safe_int(row.get("id"))
        if not reply_id:
            return []

        ticket_id = self.safe_int(row.get("tid", 0))
        user_id = self.safe_int(row.get("userid", 0))
        admin_name = row.get("admin", "")
        is_staff = 1 if admin_name else 0

        # If admin reply, user_id might be 0. We still store it 
        # but the is_staff_reply flag distinguishes it.
        date = self.map_date(row.get("date"))

        msg_dict = {
            "ticket_id": ticket_id,
            "user_id": user_id if user_id > 0 else 1,  # Fallback for FK constraint
            "message": row.get("message", ""),
            "is_staff_reply": is_staff,
            "created_at": date,
            "updated_at": date,
        }

        return [("ticket_messages", msg_dict)]
