import importlib
from typing import Any
from core.logger import get_logger
from loaders.sql_generator import SQLGenerator

logger = get_logger(__name__)

class MigrationEngine:
    """
    Core engine that drives the migration pipeline.
    Uses the Factory Design Pattern to load the appropriate extractors and transformers
    based on the source platform.
    """
    def __init__(self, source: str, input_file: str, output_file: str):
        self.source = source.lower()
        self.input_file = input_file
        self.output_file = output_file
        self.extractor_class = self._get_extractor()

    def _get_transformers(self) -> tuple:
        """
        Dynamically loads the transformers and returns:
        1. A registry for PASS 1 (currency only - must be loaded first)
        2. A registry for PASS 2 (everything else, using currency lookup)
        3. Reference to the currency_mapper for cross-mapper usage
        """
        if self.source == "whmcs":
            from transformers.whmcs.currency_mapper import CurrencyMapper
            from transformers.whmcs.user_mapper import UserMapper
            from transformers.whmcs.package_mapper import PackageMapper
            from transformers.whmcs.service_mapper import ServiceMapper
            from transformers.whmcs.invoice_mapper import InvoiceMapper
            from transformers.whmcs.order_mapper import OrderMapper
            from transformers.whmcs.ticket_mapper import TicketMapper
            from transformers.whmcs.transaction_mapper import TransactionMapper
            from transformers.whmcs.domain_mapper import DomainMapper
            from transformers.whmcs.coupon_mapper import CouponMapper
            from transformers.whmcs.cancellation_mapper import CancellationMapper

            currency_mapper = CurrencyMapper()
            user_mapper = UserMapper(currency_mapper=currency_mapper)
            package_mapper = PackageMapper()
            service_mapper = ServiceMapper(currency_mapper=currency_mapper)
            invoice_mapper = InvoiceMapper(currency_mapper=currency_mapper)
            order_mapper = OrderMapper(currency_mapper=currency_mapper)
            ticket_mapper = TicketMapper()
            transaction_mapper = TransactionMapper(currency_mapper=currency_mapper)
            domain_mapper = DomainMapper(currency_mapper=currency_mapper)
            coupon_mapper = CouponMapper()
            cancellation_mapper = CancellationMapper()

            pass1_registry = {
                "tblcurrencies": currency_mapper.map_currencies,
                "tblticketdepartments": ticket_mapper.map_departments,
            }

            pass2_registry = {
                "tblclients": user_mapper.map_clients,
                "tbladmins": user_mapper.map_admins,
                "tblproductgroups": package_mapper.map_productgroups,
                "tblproducts": package_mapper.map_products,
                "tblpricing": package_mapper.map_pricing,
                "tblhosting": service_mapper.map_hosting,
                "tblinvoices": invoice_mapper.map_invoices,
                "tblinvoiceitems": invoice_mapper.map_invoice_items,
                "tblorders": order_mapper.map_orders,
                "tbltickets": ticket_mapper.map_tickets,
                "tblticketreplies": ticket_mapper.map_replies,
                "tblaccounts": transaction_mapper.map_accounts,
                "tbldomains": domain_mapper.map_domains,
                "tblpromotions": coupon_mapper.map_promotions,
                "tblcancelrequests": cancellation_mapper.map_cancel_requests,
            }

            return pass1_registry, pass2_registry, currency_mapper
        
        return {}, {}, None

    def _get_extractor(self) -> Any:
        """
        Dynamically loads the extractor class based on the source platform.
        """
        module_name = f"extractors.{self.source}.sql_extractor"
        class_name = f"{self.source.capitalize()}SqlExtractor"
        try:
            module = importlib.import_module(module_name)
            extractor_class = getattr(module, class_name)
            logger.info(f"Successfully loaded extractor: {class_name}")
            return extractor_class
        except ImportError as e:
            logger.error(f"Failed to load extractor for source '{self.source}': {e}")
            raise ValueError(f"Extractor for '{self.source}' not found.") from e
        except AttributeError as e:
            logger.error(f"Extractor class '{class_name}' not found in module '{module_name}': {e}")
            raise ValueError(f"Extractor class '{class_name}' not found.") from e

    def run(self) -> None:
        """
        Executes the migration pipeline: Extract -> Transform -> Load.
        Uses two passes:
          Pass 1: Read currencies and department lookups (builds internal maps)
          Pass 2: Full extraction with all mappers using the lookup data
        """
        logger.info(f"Starting extraction for source: {self.source}")
        
        pass1_registry, pass2_registry, currency_mapper = self._get_transformers()
        
        # --- PASS 1: Build lookup tables (currencies, departments) ---
        logger.info("Pass 1: Building currency and department lookup tables...")
        extractor = self.extractor_class(self.input_file)
        pass1_count = 0
        for table_name, record in extractor.extract():
            if table_name in pass1_registry:
                try:
                    mapped = pass1_registry[table_name](record)
                    pass1_count += len(mapped)
                except Exception as e:
                    logger.error(f"Pass 1 error in '{table_name}': {e}")

        if currency_mapper:
            logger.info(f"Pass 1 complete. Currencies loaded: {currency_mapper.id_to_code}")
        
        # --- PASS 2: Full migration with all mappers ---
        logger.info("Pass 2: Running full migration...")
        extractor = self.extractor_class(self.input_file)
        
        # Merge both registries for pass 2
        full_registry = {**pass1_registry, **pass2_registry}
        count = 0
        
        with SQLGenerator(self.output_file) as loader:
            for table_name, record in extractor.extract():
                if table_name in full_registry:
                    try:
                        mapped_records = full_registry[table_name](record)
                        for target_table, target_record in mapped_records:
                            count += 1
                            loader.insert(target_table, target_record)
                            
                            if count % 10000 == 0:
                                logger.info(f"Transformed & generated {count} records...")
                    except Exception as e:
                        logger.error(f"Error mapping record in table '{table_name}': {e}")
                
        logger.info(f"Migration complete. Total records mapped and processed: {count}")
