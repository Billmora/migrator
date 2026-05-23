from typing import Dict, Any, List, Tuple
from transformers.base_mapper import BaseMapper
from core.logger import get_logger

logger = get_logger(__name__)

class UserMapper(BaseMapper):
    def __init__(self, currency_mapper=None):
        self.seen_emails = set()
        self.currency_mapper = currency_mapper

    def map_clients(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Maps WHMCS tblclients to Billmora users, user_billings, and user_credits.
        """
        user_id = self.safe_int(row.get("id"))
        if not user_id:
            return []

        # Handle duplicate emails to satisfy users_email_unique
        raw_email = row.get("email", "").strip()
        email = raw_email
        if not email:
            email = f"empty_{user_id}@migrated.local"
            
        if email.lower() in self.seen_emails:
            # Append suffix to make unique, e.g. name+dupID@domain.com
            parts = email.split("@", 1)
            if len(parts) == 2:
                email = f"{parts[0]}+dup{user_id}@{parts[1]}"
            else:
                email = f"{email}+dup{user_id}"
                
        self.seen_emails.add(email.lower())

        # 1. Map to users
        status_map = {
            "active": "active",
            "inactive": "inactive",
            "closed": "closed",
        }
        whmcs_status = str(row.get("status", "")).lower()
        billmora_status = status_map.get(whmcs_status, "active")

        created_at = self.map_date(row.get("datecreated"))
        email_verified = self.safe_int(row.get("email_verified", 0))

        user_dict = {
            "id": user_id,
            "first_name": row.get("firstname", ""),
            "last_name": row.get("lastname", ""),
            "email": email,
            "password": row.get("password", ""),
            "is_root_admin": 0,
            "department": None,
            "auto_credit_payment": 0,
            "status": billmora_status,
            "language": row.get("language", "en_US") or "en_US",
            "email_verified_at": created_at if email_verified else None,
            "oauth_provider": None,
            "oauth_provider_id": None,
            "remember_token": None,
            "created_at": created_at,
            "updated_at": self.map_date(row.get("updated_at", created_at)),
            "deleted_at": None
        }

        # 2. Map to user_billings
        billing_dict = {
            "user_id": user_id,
            "phone_number": row.get("phonenumber", ""),
            "company_name": row.get("companyname", ""),
            "street_address_1": row.get("address1", ""),
            "street_address_2": row.get("address2", ""),
            "city": row.get("city", ""),
            "country": row.get("country", ""),
            "state": row.get("state", ""),
            "postcode": row.get("postcode", ""),
            "created_at": created_at,
            "updated_at": created_at
        }

        # 3. Map to user_credits
        currency_id = row.get("currency", "1")
        currency_code = self.currency_mapper.get_code(currency_id) if self.currency_mapper else str(currency_id)
        credit_dict = {
            "user_id": user_id,
            "currency": currency_code, 
            "balance": self.safe_float(row.get("credit", 0.0)),
            "created_at": created_at,
            "updated_at": created_at
        }

        return [
            ("users", user_dict),
            ("user_billings", billing_dict),
            ("user_credits", credit_dict)
        ]

    def map_admins(self, row: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Admins are skipped per user request to allow manual assignment later.
        """
        return []
