import json
from typing import Dict, List, Any
from core.logger import get_logger

logger = get_logger(__name__)

class SQLGenerator:
    """
    Generates standard MySQL INSERT INTO statements and writes them in chunks
    to an output SQL file.
    """
    def __init__(self, output_path: str, chunk_size: int = 100):
        self.output_path = output_path
        self.chunk_size = chunk_size
        self.buffer: Dict[str, List[Dict[str, Any]]] = {}
        self.file = None
        self.cleaned_tables = set()

    def __enter__(self):
        # Open in utf-8 to ensure we handle any characters properly
        self.file = open(self.output_path, 'w', encoding='utf-8')
        # Write headers
        self.file.write("SET FOREIGN_KEY_CHECKS=0;\n")
        self.file.write("SET SQL_MODE='ALLOW_INVALID_DATES';\n\n")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush_all()
        if self.file:
            self.file.close()

    def _escape_value(self, value: Any) -> str:
        """
        Properly escapes strings for MySQL insertions.
        """
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        
        # If it's a dict or list, it's likely a JSON field, serialize it first
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
            
        value = str(value)
        # Handle escapes
        value = value.replace("\\", "\\\\")
        value = value.replace("'", "\\'")
        value = value.replace("\"", "\\\"")
        value = value.replace("\n", "\\n")
        value = value.replace("\r", "\\r")
        return f"'{value}'"

    def insert(self, table: str, data: Dict[str, Any]):
        """
        Queues a dictionary of data to be inserted into a table.
        """
        if table not in self.buffer:
            self.buffer[table] = []
        
        # Emit DELETE FROM before first insert into this table
        if table not in self.cleaned_tables:
            self.file.write(f"DELETE FROM `{table}`;\n")
            self.cleaned_tables.add(table)
            
        self.buffer[table].append(data)
        
        if len(self.buffer[table]) >= self.chunk_size:
            self.flush_table(table)

    def flush_table(self, table: str):
        """
        Flushes the current buffer for a specific table to the file as an extended insert.
        """
        if not self.buffer.get(table):
            return
            
        rows = self.buffer[table]
        
        # Assuming all dicts in a batch have the same keys
        columns = list(rows[0].keys())
        cols_str = ", ".join(f"`{col}`" for col in columns)
        
        values_strings = []
        for row in rows:
            # We map to the columns of the first row to keep order consistent
            row_vals = [self._escape_value(row.get(col)) for col in columns]
            values_strings.append("(" + ", ".join(row_vals) + ")")
            
        insert_stmt = f"INSERT INTO `{table}` ({cols_str}) VALUES\n"
        insert_stmt += ",\n".join(values_strings) + ";\n\n"
        
        self.file.write(insert_stmt)
        self.buffer[table] = []

    def flush_all(self):
        """
        Flushes all remaining buffered rows.
        """
        for table in list(self.buffer.keys()):
            self.flush_table(table)
