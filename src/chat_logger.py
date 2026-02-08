"""
Chat Logger - Logs chat interactions to BigQuery or local CSV
"""
import logging
import json
import os
import csv
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid

logger = logging.getLogger(__name__)


class ChatLogger:
    """
    Logs chat interactions to BigQuery or local CSV file.

    Logs include: session_id, timestamp, model, user_query, tools_used, response, user_feedback
    """

    def __init__(
        self,
        enabled: bool = False,
        log_to_bigquery: bool = False,
        use_default_table: bool = True,
        custom_project: Optional[str] = None,
        custom_dataset: Optional[str] = None,
        custom_table: Optional[str] = None,
        local_csv_path: str = "chat_logs.csv"
    ):
        """
        Initialize chat logger.

        Args:
            enabled: Whether logging is enabled
            log_to_bigquery: Log to BigQuery (True) or local CSV (False)
            use_default_table: Use default BigQuery table
            custom_project: Custom BigQuery project (if not using default)
            custom_dataset: Custom BigQuery dataset (if not using default)
            custom_table: Custom BigQuery table name (if not using default)
            local_csv_path: Path to local CSV file
        """
        self.enabled = enabled
        self.log_to_bigquery = log_to_bigquery
        self.use_default_table = use_default_table
        self.local_csv_path = local_csv_path

        # Default BigQuery table
        self.default_project = "hudhud-demo"
        self.default_dataset = "penny_demo"
        self.default_table = "chat_logs"

        # Custom or default
        if use_default_table:
            self.bq_project = self.default_project
            self.bq_dataset = self.default_dataset
            self.bq_table = self.default_table
        else:
            self.bq_project = custom_project or self.default_project
            self.bq_dataset = custom_dataset or self.default_dataset
            self.bq_table = custom_table or self.default_table

        self.bq_client = None
        self.bq_available = False

        # Initialize BigQuery client if enabled
        if self.enabled and self.log_to_bigquery:
            self._init_bigquery()

    def _init_bigquery(self):
        """Initialize BigQuery client and ensure table exists."""
        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account

            logger.info(f"Initializing BigQuery logging to {self.bq_project}.{self.bq_dataset}.{self.bq_table}")

            # Try to create client with service account
            sa_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

            if sa_key_path and os.path.exists(sa_key_path):
                logger.info(f"Using service account from: {sa_key_path}")
                credentials = service_account.Credentials.from_service_account_file(
                    sa_key_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                self.bq_client = bigquery.Client(
                    credentials=credentials,
                    project=self.bq_project
                )
                logger.info(f"BigQuery client created with service account")
            else:
                logger.info(f"No service account found. Trying default credentials. SA_KEY_PATH={sa_key_path}")
                # Try default credentials
                self.bq_client = bigquery.Client(project=self.bq_project)
                logger.info(f"BigQuery client created with default credentials")

            # Ensure table exists
            logger.info("Ensuring BigQuery table exists...")
            self._ensure_table_exists()

            self.bq_available = True
            logger.info(f"✓ BigQuery logging initialized: {self.bq_project}.{self.bq_dataset}.{self.bq_table}")

        except Exception as e:
            logger.error(f"❌ BigQuery initialization failed: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.warning(f"Falling back to local CSV logging.")
            self.bq_available = False
            self.log_to_bigquery = False

    def _ensure_table_exists(self):
        """Ensure BigQuery table exists, create if not."""
        try:
            from google.cloud import bigquery

            # Check if dataset exists
            dataset_id = f"{self.bq_project}.{self.bq_dataset}"
            try:
                self.bq_client.get_dataset(dataset_id)
                logger.info(f"✓ BigQuery dataset exists: {dataset_id}")
            except Exception:
                # Dataset doesn't exist, create it
                dataset = bigquery.Dataset(dataset_id)
                dataset.location = "US"
                dataset = self.bq_client.create_dataset(dataset, exists_ok=True)
                logger.info(f"✓ Created BigQuery dataset: {dataset_id}")

            # Define table schema
            table_id = f"{self.bq_project}.{self.bq_dataset}.{self.bq_table}"

            schema = [
                bigquery.SchemaField("session_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("model", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("user_query", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("tools_used", "STRING", mode="NULLABLE"),  # JSON array as string
                bigquery.SchemaField("response", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("user_feedback", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("token_count", "STRING", mode="NULLABLE"),  # JSON object as string
            ]

            # Check if table exists
            try:
                self.bq_client.get_table(table_id)
                logger.info(f"✓ BigQuery table exists: {table_id}")
            except Exception:
                # Table doesn't exist, create it
                table = bigquery.Table(table_id, schema=schema)
                table = self.bq_client.create_table(table)
                logger.info(f"✓ Created BigQuery table: {table_id}")

        except Exception as e:
            logger.error(f"Error ensuring BigQuery table exists: {e}")
            raise

    def log_interaction(
        self,
        session_id: str,
        model: str,
        user_query: str,
        tools_used: List[str],
        response: str,
        user_feedback: str = "NA",
        token_count: Optional[Dict[str, int]] = None
    ):
        """
        Log a chat interaction.

        Args:
            session_id: Unique session identifier
            model: Model name used
            user_query: User's question
            tools_used: List of tools called by agent
            response: Agent's response
            user_feedback: User feedback (upvote/downvote/NA)
            token_count: Token usage dict with input_token_count, output_token_count, total_token_count
        """
        if not self.enabled:
            return

        try:
            # Prepare log entry
            log_entry = {
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "model": model,
                "user_query": user_query,
                "tools_used": json.dumps(tools_used),  # Convert list to JSON string
                "response": response,
                "user_feedback": user_feedback,
                "token_count": json.dumps(token_count) if token_count else json.dumps({})
            }

            # Try BigQuery first if enabled
            logger.debug(f"Logging flags: log_to_bigquery={self.log_to_bigquery}, bq_available={self.bq_available}")

            if self.log_to_bigquery and self.bq_available:
                try:
                    logger.info(f"Attempting to log to BigQuery...")
                    self._log_to_bigquery(log_entry)
                    logger.info(f"✓ Logged to BigQuery: {session_id}")
                    return
                except Exception as e:
                    logger.warning(f"BigQuery logging failed: {e}. Falling back to CSV.")
            else:
                if not self.log_to_bigquery:
                    logger.info(f"BigQuery logging disabled (log_to_bigquery=False). Using CSV.")
                elif not self.bq_available:
                    logger.info(f"BigQuery not available (bq_available=False). Using CSV.")

            # Fallback to local CSV
            self._log_to_csv(log_entry)
            logger.info(f"✓ Logged to CSV: {session_id}")

        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")

    def _log_to_bigquery(self, log_entry: Dict[str, Any]):
        """Log to BigQuery table."""
        from google.cloud import bigquery

        table_id = f"{self.bq_project}.{self.bq_dataset}.{self.bq_table}"

        # Prepare row for BigQuery (keep timestamp as ISO string for JSON serialization)
        # BigQuery will automatically parse the ISO timestamp string
        rows_to_insert = [log_entry]

        # Insert row
        errors = self.bq_client.insert_rows_json(table_id, rows_to_insert)

        if errors:
            raise Exception(f"BigQuery insert errors: {errors}")

    def _log_to_csv(self, log_entry: Dict[str, Any]):
        """Log to local CSV file (append mode)."""
        file_exists = os.path.exists(self.local_csv_path)

        # Define CSV columns
        fieldnames = [
            "session_id",
            "timestamp",
            "model",
            "user_query",
            "tools_used",
            "response",
            "user_feedback",
            "token_count"
        ]

        # Append to CSV
        with open(self.local_csv_path, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # Write header if file is new
            if not file_exists:
                writer.writeheader()

            writer.writerow(log_entry)

    @staticmethod
    def generate_session_id() -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())


def create_chat_logger(
    enabled: bool = False,
    log_to_bigquery: bool = False,
    use_default_table: bool = True,
    **kwargs
) -> ChatLogger:
    """
    Convenience function to create a chat logger.

    Args:
        enabled: Whether logging is enabled
        log_to_bigquery: Log to BigQuery (True) or local CSV (False)
        use_default_table: Use default BigQuery table
        **kwargs: Additional arguments for ChatLogger

    Returns:
        ChatLogger instance
    """
    return ChatLogger(
        enabled=enabled,
        log_to_bigquery=log_to_bigquery,
        use_default_table=use_default_table,
        **kwargs
    )
