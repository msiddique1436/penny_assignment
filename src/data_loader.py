"""
Data loader module for loading CSV procurement data into MongoDB.
Handles batch loading, data cleaning, and validation.
"""
import csv
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import re
from tqdm import tqdm

from src.mongo_client import MongoDBClient
import config

logger = logging.getLogger(__name__)


class ProcurementDataLoader:
    """
    Loads procurement data from CSV file into MongoDB.
    Handles data cleaning, transformation, and batch insertion.
    """

    def __init__(self, mongo_client: MongoDBClient, csv_path: Path = config.CSV_FILE):
        """
        Initialize data loader.

        Args:
            mongo_client: MongoDB client instance
            csv_path: Path to CSV file
        """
        self.mongo_client = mongo_client
        self.csv_path = csv_path
        self.field_mapping = config.CSV_FIELD_MAPPING

    @staticmethod
    def clean_currency(value: str) -> float:
        """
        Clean currency string and convert to float.

        Args:
            value: Currency string (e.g., "$1,234.56")

        Returns:
            float: Numeric value
        """
        if not value or value.strip() == "":
            return 0.0

        try:
            # Remove $ and commas
            cleaned = value.replace("$", "").replace(",", "").strip()
            return float(cleaned) if cleaned else 0.0
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def clean_numeric(value: str) -> float:
        """
        Clean numeric string and convert to float.

        Args:
            value: Numeric string

        Returns:
            float: Numeric value
        """
        if not value or value.strip() == "":
            return 0.0

        try:
            cleaned = value.replace(",", "").strip()
            return float(cleaned) if cleaned else 0.0
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def clean_string(value: str) -> str:
        """
        Clean string value.

        Args:
            value: String to clean

        Returns:
            str: Cleaned string (empty string if None)
        """
        if value is None:
            return ""
        return value.strip()

    @staticmethod
    def parse_date(date_str: str) -> Optional[Dict[str, Any]]:
        """
        Parse date string and extract components.

        Args:
            date_str: Date string in MM/DD/YYYY format

        Returns:
            Dict with parsed date components or None if parsing fails
        """
        if not date_str or date_str.strip() == "":
            return None

        try:
            # Handle MM/DD/YYYY format
            match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str.strip())
            if match:
                month, day, year = match.groups()
                month = int(month)
                day = int(day)
                year = int(year)

                # Create datetime object for easier querying
                try:
                    dt = datetime(year, month, day)
                    return {
                        "original": date_str,
                        "year": year,
                        "month": month,
                        "day": day,
                        "datetime": dt,
                        "quarter": (month - 1) // 3 + 1,  # Calendar quarter (1-4)
                    }
                except ValueError:
                    # Invalid date (e.g., Feb 30)
                    return None

            return None
        except Exception:
            return None

    @staticmethod
    def calculate_fiscal_quarter(date_str: str, fiscal_year: str) -> Optional[str]:
        """
        Calculate California fiscal quarter from date.
        California fiscal year runs July 1 - June 30.
        Q1: Jul-Sep, Q2: Oct-Dec, Q3: Jan-Mar, Q4: Apr-Jun

        Args:
            date_str: Date string in MM/DD/YYYY format
            fiscal_year: Fiscal year string (e.g., "2013-2014")

        Returns:
            Fiscal quarter string (e.g., "Q1", "Q2") or None
        """
        parsed = ProcurementDataLoader.parse_date(date_str)
        if not parsed:
            return None

        month = parsed["month"]

        if month in [7, 8, 9]:
            return "Q1"
        elif month in [10, 11, 12]:
            return "Q2"
        elif month in [1, 2, 3]:
            return "Q3"
        elif month in [4, 5, 6]:
            return "Q4"

        return None

    def parse_csv_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse and clean a CSV row into MongoDB document format.

        Args:
            row: Raw CSV row as dict

        Returns:
            Cleaned document dict
        """
        doc = {}

        # Map and clean each field
        for csv_field, mongo_field in self.field_mapping.items():
            value = row.get(csv_field, "")

            # Handle specific field types
            if mongo_field in ["quantity", "unit_price", "total_price"]:
                if mongo_field == "quantity":
                    doc[mongo_field] = self.clean_numeric(value)
                else:
                    doc[mongo_field] = self.clean_currency(value)

            elif mongo_field in ["supplier_code", "class_code", "family_code", "segment_code"]:
                # Keep codes as strings but clean them
                doc[mongo_field] = self.clean_string(value)

            elif mongo_field in ["creation_date", "purchase_date"]:
                # Store original string for now (we'll add parsed versions)
                doc[mongo_field] = self.clean_string(value)

            else:
                # All other fields are strings
                doc[mongo_field] = self.clean_string(value)

        # Parse creation_date and add structured fields
        if doc.get("creation_date"):
            parsed_date = self.parse_date(doc["creation_date"])
            if parsed_date:
                doc["creation_date_parsed"] = parsed_date["datetime"]
                doc["creation_year"] = parsed_date["year"]
                doc["creation_month"] = parsed_date["month"]
                doc["creation_quarter"] = parsed_date["quarter"]

                # Calculate fiscal quarter
                fiscal_quarter = self.calculate_fiscal_quarter(
                    doc["creation_date"],
                    doc.get("fiscal_year", "")
                )
                if fiscal_quarter:
                    doc["fiscal_quarter"] = fiscal_quarter

        # Parse purchase_date if present
        if doc.get("purchase_date"):
            parsed_date = self.parse_date(doc["purchase_date"])
            if parsed_date:
                doc["purchase_date_parsed"] = parsed_date["datetime"]

        return doc

    def load_data(
        self,
        batch_size: int = config.DATA_LOAD_BATCH_SIZE,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        start_from: int = 0
    ) -> Dict[str, Any]:
        """
        Load CSV data into MongoDB in batches.

        Args:
            batch_size: Number of rows to process per batch
            progress_callback: Optional callback function(current, total) for progress updates
            start_from: Row number to start from (for resuming)

        Returns:
            Dict with loading statistics
        """
        logger.info(f"Starting data load from {self.csv_path}")

        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        stats = {
            "total_rows_processed": 0,
            "total_rows_inserted": 0,
            "total_rows_skipped": 0,
            "errors": [],
        }

        try:
            # First, count total rows for progress bar
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                total_rows = sum(1 for _ in f) - 1  # -1 for header

            logger.info(f"Total rows to process: {total_rows:,}")

            # Open CSV file
            with open(self.csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                batch = []
                row_num = 0

                # Create progress bar
                pbar = tqdm(total=total_rows, desc="Loading data", unit="rows")

                for row in reader:
                    row_num += 1

                    # Skip rows if resuming
                    if row_num < start_from:
                        pbar.update(1)
                        continue

                    try:
                        # Parse and clean row
                        doc = self.parse_csv_row(row)
                        batch.append(doc)

                        # Insert batch when it reaches batch_size
                        if len(batch) >= batch_size:
                            self.mongo_client.collection.insert_many(batch)
                            stats["total_rows_inserted"] += len(batch)
                            batch = []

                            # Update progress
                            pbar.update(batch_size)
                            if progress_callback:
                                progress_callback(row_num, total_rows)

                    except Exception as e:
                        logger.warning(f"Error processing row {row_num}: {e}")
                        stats["errors"].append({"row": row_num, "error": str(e)})
                        stats["total_rows_skipped"] += 1

                    stats["total_rows_processed"] += 1

                # Insert remaining rows in batch
                if batch:
                    self.mongo_client.collection.insert_many(batch)
                    stats["total_rows_inserted"] += len(batch)
                    pbar.update(len(batch))

                pbar.close()

            logger.info(f"Data load completed. Processed: {stats['total_rows_processed']:,}, "
                       f"Inserted: {stats['total_rows_inserted']:,}, "
                       f"Skipped: {stats['total_rows_skipped']:,}")

            return stats

        except Exception as e:
            logger.error(f"Fatal error during data load: {e}")
            stats["errors"].append({"fatal": True, "error": str(e)})
            return stats

    def validate_data_load(self) -> Dict[str, Any]:
        """
        Validate the loaded data.

        Returns:
            Dict with validation results
        """
        logger.info("Validating loaded data...")

        try:
            col = self.mongo_client.collection

            # Count documents
            total_count = col.count_documents({})

            # Check for documents with missing critical fields
            missing_creation_date = col.count_documents({"creation_date": ""})
            missing_total_price = col.count_documents({"total_price": {"$exists": False}})

            # Check for zero/null prices
            zero_price_count = col.count_documents({"total_price": 0})

            # Get sample document
            sample = col.find_one()

            validation_results = {
                "total_documents": total_count,
                "missing_creation_date": missing_creation_date,
                "missing_total_price": missing_total_price,
                "zero_price_count": zero_price_count,
                "sample_document": sample,
                "validation_passed": total_count > 0 and missing_total_price == 0
            }

            logger.info(f"Validation complete: {total_count:,} documents loaded")

            return validation_results

        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return {"error": str(e), "validation_passed": False}


def load_procurement_data(
    mongo_client: MongoDBClient,
    csv_path: Path = config.CSV_FILE,
    batch_size: int = config.DATA_LOAD_BATCH_SIZE,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Dict[str, Any]:
    """
    Convenience function to load procurement data.

    Args:
        mongo_client: MongoDB client
        csv_path: Path to CSV file
        batch_size: Batch size for insertion
        progress_callback: Optional progress callback

    Returns:
        Dict with loading statistics
    """
    loader = ProcurementDataLoader(mongo_client, csv_path)
    stats = loader.load_data(batch_size, progress_callback)

    # Create indexes after loading
    if stats["total_rows_inserted"] > 0:
        logger.info("Creating indexes...")
        mongo_client.create_indexes()

    return stats
