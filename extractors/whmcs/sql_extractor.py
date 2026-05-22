import logging
from typing import Generator, Any, Tuple
from extractors.base import BaseExtractor
from extractors.utils.sql_parser import SqlParser

logger = logging.getLogger(__name__)

class WhmcsSqlExtractor(BaseExtractor):
    """
    WHMCS Extractor to read a raw MySQL dump file line-by-line.
    Uses generators to minimize RAM usage.
    """
    
    def extract(self) -> Generator[Tuple[str, dict[str, Any]], None, None]:
        """
        Reads the SQL dump file line-by-line, identifies INSERT statements,
        parses them, and yields each row as a dictionary.
        
        Yields:
            Tuple[str, dict]: (table_name, record_dictionary)
        """
        logger.info(f"Starting to read WHMCS SQL dump: {self.file_path}")
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                accumulating = False
                stmt_buffer = []
                start_line = 0

                for line_num, line in enumerate(f, 1):
                    if not accumulating:
                        if line.startswith("INSERT INTO"):
                            if line.strip().endswith(";"):
                                # One-liner
                                yield from self._process_statement(line, line_num)
                            else:
                                accumulating = True
                                stmt_buffer.append(line)
                                start_line = line_num
                    else:
                        stmt_buffer.append(line)
                        if line.strip().endswith(";"):
                            accumulating = False
                            full_stmt = "".join(stmt_buffer)
                            yield from self._process_statement(full_stmt, start_line)
                            stmt_buffer = []
                                
        except FileNotFoundError:
            logger.error(f"SQL dump file not found: {self.file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading SQL dump file: {e}")
            raise

    def _process_statement(self, stmt: str, line_num: int) -> Generator[Tuple[str, dict[str, Any]], None, None]:
        table_name, columns, rows = SqlParser.parse_insert_statement(stmt)
        
        if not table_name:
            logger.warning(f"Failed to parse INSERT statement on line {line_num}")
            return
            
        if not columns:
            for row in rows:
                record = {f"col_{i}": val for i, val in enumerate(row)}
                yield table_name, record
        else:
            for row in rows:
                # Truncate row or columns if mismatch
                record = dict(zip(columns, row))
                yield table_name, record
