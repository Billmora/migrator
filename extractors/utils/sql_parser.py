import re
from typing import List, Tuple, Optional

class SqlParser:
    """
    Utility class to parse MySQL dump extended INSERT statements.
    """

    @staticmethod
    def parse_insert_statement(line: str) -> Tuple[Optional[str], List[str], List[List[str]]]:
        """
        Parses an INSERT INTO statement and extracts the table name, columns, and rows.
        
        Args:
            line (str): The raw SQL INSERT statement.
            
        Returns:
            Tuple[str, List[str], List[List[str]]]: (table_name, columns, list_of_rows)
        """
        # Match 'INSERT INTO `table_name` (`col1`, `col2`) VALUES' or 'INSERT INTO `table_name` VALUES'
        insert_regex = re.compile(r"INSERT\s+INTO\s+`?([a-zA-Z0-9_]+)`?\s*(?:\((.*?)\))?\s*VALUES\s*(.*);", re.IGNORECASE | re.DOTALL)
        match = insert_regex.match(line.strip())
        
        if not match:
            return None, [], []
            
        table_name = match.group(1)
        columns_str = match.group(2)
        values_str = match.group(3)
        
        columns = []
        if columns_str:
            # Extract column names, removing backticks and spaces
            columns = [col.strip(" `") for col in columns_str.split(",")]
            
        # Parse values
        rows = SqlParser.parse_values(values_str)
        
        return table_name, columns, rows

    @staticmethod
    def parse_values(values_str: str) -> List[List[str]]:
        """
        Parses the VALUES section of an extended INSERT statement.
        Robustly handles commas and escaped quotes inside strings.
        
        Args:
            values_str (str): The string containing values e.g., "(1, 'a, b', 'c\'d'), (2, 'e', 'f')"
            
        Returns:
            List[List[str]]: A list of rows, where each row is a list of parsed string values.
        """
        rows = []
        current_row = []
        current_val = []
        
        in_string = False
        string_char = None
        escape_next = False
        in_tuple = False
        
        for char in values_str:
            if escape_next:
                # We append the escape character and the escaped character
                current_val.append(char)
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                current_val.append(char)
                continue
                
            if in_string:
                current_val.append(char)
                if char == string_char:
                    in_string = False
            else:
                if char in ("'", '"'):
                    in_string = True
                    string_char = char
                    current_val.append(char)
                elif char == '(':
                    in_tuple = True
                    current_row = []
                    current_val = []
                elif char == ')':
                    if in_tuple:
                        # End of a row
                        if current_val or (not current_val and current_row):
                            # Add the last value
                            val_str = "".join(current_val).strip()
                            if val_str or (not val_str and current_row):
                                current_row.append(SqlParser._clean_value(val_str))
                        if current_row:
                            rows.append(current_row)
                        current_val = []
                        in_tuple = False
                elif char == ',':
                    if in_tuple:
                        # End of a value
                        val_str = "".join(current_val).strip()
                        current_row.append(SqlParser._clean_value(val_str))
                        current_val = []
                else:
                    if in_tuple:
                        current_val.append(char)
                        
        return rows

    @staticmethod
    def _clean_value(val_str: str) -> Optional[str]:
        """
        Cleans a raw MySQL value string by removing outer quotes and unescaping.
        Returns None for NULL values.
        """
        if val_str.upper() == 'NULL':
            return None
            
        if val_str.startswith("'") and val_str.endswith("'") and len(val_str) >= 2:
            inner = val_str[1:-1]
            return inner.replace("\\'", "'").replace("\\\\", "\\").replace('\\"', '"').replace('\\n', '\n').replace('\\r', '\r')
            
        if val_str.startswith('"') and val_str.endswith('"') and len(val_str) >= 2:
            inner = val_str[1:-1]
            return inner.replace("\\'", "'").replace("\\\\", "\\").replace('\\"', '"').replace('\\n', '\n').replace('\\r', '\r')
            
        return val_str
