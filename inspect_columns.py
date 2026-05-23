import re

TARGET_TABLES = [
    "tblproductconfiggroups", "tblproductconfigoptions", "tblproductconfigoptionssub",
    "tblproductconfiglinks", "tblhostingconfigoptions",
    "tblpricing", "tblhosting", "tbltickets", "tblticketreplies",
    "tblcancelrequests", "tblorders", "tbldomains", "tblaccounts",
    "tblcredit",
]

found = set()
with open("octaviai76_web_billing.sql", "r", encoding="utf-8") as f:
    for line in f:
        if line.startswith("INSERT INTO"):
            m = re.match(r"INSERT INTO `([^`]+)`\s*\(([^)]+)\)", line)
            if m and m.group(1) in TARGET_TABLES and m.group(1) not in found:
                table = m.group(1)
                cols = [c.strip().strip("`") for c in m.group(2).split(",")]
                print(f"\n=== {table} ({len(cols)} columns) ===")
                for i, col in enumerate(cols):
                    print(f"  [{i}] {col}")
                found.add(table)
                if found == set(TARGET_TABLES):
                    break

missing = set(TARGET_TABLES) - found
if missing:
    print(f"\nNo INSERT data found for: {missing}")
