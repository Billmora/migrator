import argparse
import sys
from core.logger import get_logger
from core.engine import MigrationEngine

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Billmora Migrator Tool")
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["whmcs"],
        help="The source system to migrate from."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="The path to the SQL dump file to process."
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="The path where the output SQL file should be saved."
    )
    
    args = parser.parse_args()
    
    logger.info(f"Starting migration from {args.source}")
    logger.info(f"Input file: {args.input}")
    logger.info(f"Output file: {args.output}")
    
    try:
        engine = MigrationEngine(source=args.source, input_file=args.input, output_file=args.output)
        engine.run()
        logger.info("Migration completed successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
