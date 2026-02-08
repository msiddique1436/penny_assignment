"""
Configuration module for AI-Powered Procurement Assistant.
Follows the pattern from dot_na_config.py with environment variable support.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# DIRECTORIES
# ============================================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"
SRC_DIR = BASE_DIR / "src"
PAGES_DIR = BASE_DIR / "pages"

# ============================================================================
# DATA FILES
# ============================================================================
CSV_FILE = DATA_DIR / "PURCHASE ORDER DATA EXTRACT 2012-2015_0.csv"
SAMPLE_QUERIES_FILE = DATA_DIR / "sample_queries.json"

# ============================================================================
# MONGODB CONFIGURATION
# ============================================================================
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "procurement_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "procurement_orders")

# Connection timeout in milliseconds
MONGO_TIMEOUT_MS = int(os.getenv("MONGO_TIMEOUT_MS", "5000"))

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

# Gemini Configuration (for Vertex AI / ADC mode)
VERTEX_PROJECT = os.getenv("VERTEX_PROJECT", "hudhud-demo")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "global")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

# Gemini API Key (supports multiple env var names for unified SDK)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY") or ""

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID", "")

# Generation Configuration
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 2048*4
QUERY_GENERATION_TEMPERATURE = 0.2  # Lower for more deterministic query generation

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================
APP_TITLE = "AI-Powered Procurement Assistant"
APP_ICON = "🛒"
APP_LAYOUT = "wide"

# Data Loading
DATA_LOAD_BATCH_SIZE = 1000  # Number of rows to process at once

# Query Settings
MAX_QUERY_RESULTS = 100  # Maximum number of results to return
QUERY_TIMEOUT_SECONDS = 30  # Maximum time for query execution

# UI Settings
SAMPLE_QUERY_COUNT = 6  # Number of sample queries to display

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# CSV FIELD MAPPING
# ============================================================================
# Maps CSV column names to MongoDB field names (using snake_case)
CSV_FIELD_MAPPING = {
    "Creation Date": "creation_date",
    "Purchase Date": "purchase_date",
    "Fiscal Year": "fiscal_year",
    "LPA Number": "lpa_number",
    "Purchase Order Number": "purchase_order_number",
    "Requisition Number": "requisition_number",
    "Acquisition Type": "acquisition_type",
    "Sub-Acquisition Type": "sub_acquisition_type",
    "Acquisition Method": "acquisition_method",
    "Sub-Acquisition Method": "sub_acquisition_method",
    "Department Name": "department_name",
    "Supplier Code": "supplier_code",
    "Supplier Name": "supplier_name",
    "Supplier Qualifications": "supplier_qualifications",
    "Supplier Zip Code": "supplier_zip_code",
    "CalCard": "cal_card",
    "Item Name": "item_name",
    "Item Description": "item_description",
    "Quantity": "quantity",
    "Unit Price": "unit_price",
    "Total Price": "total_price",
    "Classification Codes": "classification_codes",
    "Normalized UNSPSC": "normalized_unspsc",
    "Commodity Title": "commodity_title",
    "Class": "class_code",
    "Class Title": "class_title",
    "Family": "family_code",
    "Family Title": "family_title",
    "Segment": "segment_code",
    "Segment Title": "segment_title",
    "Location": "location",
}

# ============================================================================
# VALIDATION
# ============================================================================
def validate_config():
    """Validate that required paths and configurations exist."""
    errors = []

    # Check that data file exists
    if not CSV_FILE.exists():
        errors.append(f"CSV file not found: {CSV_FILE}")

    # Create directories if they don't exist
    for directory in [DATA_DIR, PROMPTS_DIR, SRC_DIR, PAGES_DIR]:
        directory.mkdir(exist_ok=True)

    if errors:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(errors))

    return True


# Validate on import
if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(f"Warning: {e}")
