import re

tables = set()
with open("octaviai76_web_billing.sql", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("INSERT INTO"):
            m = re.match(r"INSERT INTO `([^`]+)`", line)
            if m:
                tables.add(m.group(1))

print("=== Semua tabel WHMCS yang berisi data ===")
for t in sorted(tables):
    print(t)
print(f"\nTotal: {len(tables)} tabel")
