from extractors.utils.sql_parser import SqlParser
sql = "INSERT INTO `tblclients` (`id`, `name`, `notes`) VALUES (1, 'John Doe', 'O\\'Connor is a good client, \\nwith commas'), (2, 'Jane Doe', NULL);"
table_name, columns, rows = SqlParser.parse_insert_statement(sql)
print(f'Table: {table_name}')
print(f'Columns: {columns}')
for row in rows:
    print(f'Row: {row}')
