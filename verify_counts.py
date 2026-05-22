import re
from collections import defaultdict

counts = defaultdict(int)
current_table = None

with open("billmora_import.sql", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("INSERT INTO"):
            match = re.search(r"INSERT INTO `([^`]+)`", line)
            if match:
                current_table = match.group(1)
        elif current_table and line.startswith("("):
            counts[current_table] += 1
            if line.endswith(";"):
                current_table = None

print("=== Statistik Migrasi Data ===")
for table, count in counts.items():
    print(f"{table}: {count} baris")
