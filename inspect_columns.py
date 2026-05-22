import re

TARGET_TABLES = [
    "tblcurrencies", "tblorders", "tbltickets", "tblticketreplies",
    "tblticketdepartments", "tblaccounts", "tbldomains",
    "tblpromotions", "tblcancelrequests"
]

with open("octaviai76_web_billing.sql", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("INSERT INTO"):
            m = re.match(r"INSERT INTO `([^`]+)`\s*\(([^)]+)\)", line)
            if m and m.group(1) in TARGET_TABLES:
                table = m.group(1)
                cols = [c.strip().strip("`") for c in m.group(2).split(",")]
                print(f"\n=== {table} ({len(cols)} columns) ===")
                for i, col in enumerate(cols):
                    print(f"  [{i}] {col}")
                TARGET_TABLES.remove(table)
                if not TARGET_TABLES:
                    break

if TARGET_TABLES:
    print(f"\nTidak ditemukan data INSERT untuk: {TARGET_TABLES}")
