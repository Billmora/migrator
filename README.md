<p align="center">
  <a href="https://billmora.com">
    <img src="https://media.billmora.com/logo/main-bgnone.png" width="128px" alt="Billmora" style="border-radius: 15px;">
  </a>
</p>

<h1 align="center">Billmora Migrator</h1>

<p align="center">
  Official data migration tool for transitioning to Billmora.<br>
  A flexible and extensible tool supporting migrations from various billing platforms to the Billmora schema.
</p>

## Overview

The **Billmora Migrator** is a Python-based utility designed to parse SQL dumps from other billing platforms (e.g., WHMCS, Blesta, ClientExec, WemX) and transform them into a fully compatible `billmora_import.sql` file that can be directly imported into your Billmora database.

It uses a fast, low-memory stream parsing engine and a **Two-Pass Architecture** to handle complex relational data (like multi-currency pricing, configurable options/variants, and service provisioning configurations) without requiring a live database connection to the source platform.

## Requirements

- Python 3.8+
- The SQL dump of your source database (e.g., `source_db.sql`)

## Supported Platforms

You can specify the source platform using the `--source` argument. Currently supported sources include:

- `whmcs` (More platforms like Blesta, ClientExec, and WemX can be added easily via the extensible extractor/mapper system)

## Installation

First, clone the repository to your local machine:

```bash
git clone https://github.com/Billmora/migrator.git
cd migrator
```

## Usage Commands

Here are the primary commands you can use with this migrator:

### 1. Run the Migrator

This is the main command to execute the migration. It will read your source SQL dump and generate a new SQL file formatted for Billmora.

```bash
python main.py --source <platform_name> --input <source_db.sql> --output <output_import.sql>
```

**Example:**

```bash
python main.py --source whmcs --input backup_billing.sql --output billmora_import.sql
```

### 2. Verify Generated SQL (Statistics)

After generating the `billmora_import.sql` file, you can run this utility to quickly check the number of rows generated for each Billmora table. This helps ensure all data was migrated successfully.

```bash
python verify_counts.py billmora_import.sql
```

### 3. Utility: List Tables

If you want to see all the tables present in your source SQL dump, use this command:

```bash
python list_tables.py <source_db.sql>
```

### 4. Utility: Inspect Columns

If you need to debug or verify the exact column names being extracted from a specific table in the source SQL dump:

```bash
python inspect_columns.py <source_db.sql> <table_name>
```

**Example:**

```bash
python inspect_columns.py backup_billing.sql users_table
```

## How It Works

1. **Pass 1 (Aggregation):** The engine reads through the SQL dump to build in-memory lookups for currencies, package pricing cycles, configurable options (variants), and hosting selections.
2. **Pass 2 (Transformation):** The engine reads the SQL dump a second time, mapping the data into Billmora's schema.
3. **Generation:** The transformed data is safely written out as standard `INSERT INTO` statements with `FOREIGN_KEY_CHECKS=0` to ensure smooth importation.

## Importing to Billmora

Once you have generated the `billmora_import.sql` file, you can import it directly into your Billmora MySQL/MariaDB database:

```bash
mysql -u your_user -p your_billmora_database < billmora_import.sql
```

> **Note:** The migrator automatically includes `DELETE FROM` statements for the tables it migrates, so running the import will overwrite existing data in those specific tables. Default seed data (like the default currency) is preserved or properly linked.

## Support & Community

- [Website](https://billmora.com)
- [Documentation](https://billmora.com/docs/introduction)
- [Discord Community](https://dsc.gg/billmora)
