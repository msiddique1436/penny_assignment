"""
MongoDB client module for managing database connections and operations.
"""
import logging
from typing import Optional, Dict, List, Any
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from pymongo.collection import Collection
from pymongo.database import Database

import config

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    MongoDB client wrapper for procurement data operations.
    Handles connection management, collection access, and indexing.
    """

    def __init__(
        self,
        uri: str = config.MONGO_URI,
        db_name: str = config.MONGO_DB_NAME,
        collection_name: str = config.MONGO_COLLECTION,
        timeout_ms: int = config.MONGO_TIMEOUT_MS
    ):
        """
        Initialize MongoDB client.

        Args:
            uri: MongoDB connection URI
            db_name: Database name
            collection_name: Collection name
            timeout_ms: Server selection timeout in milliseconds
        """
        self.uri = uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.timeout_ms = timeout_ms

        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._collection: Optional[Collection] = None

    def connect(self) -> bool:
        """
        Establish connection to MongoDB.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to MongoDB at {self.uri}")
            self._client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=self.timeout_ms
            )

            # Test connection
            self._client.admin.command('ping')

            self._db = self._client[self.db_name]
            self._collection = self._db[self.collection_name]

            logger.info(f"Successfully connected to database '{self.db_name}', collection '{self.collection_name}'")
            return True

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during MongoDB connection: {e}")
            return False

    def disconnect(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")
            self._client = None
            self._db = None
            self._collection = None

    def is_connected(self) -> bool:
        """
        Check if MongoDB connection is active.

        Returns:
            bool: True if connected, False otherwise
        """
        if self._client is None:
            return False

        try:
            self._client.admin.command('ping')
            return True
        except Exception:
            return False

    @property
    def collection(self) -> Collection:
        """
        Get the MongoDB collection.

        Returns:
            Collection: MongoDB collection instance

        Raises:
            RuntimeError: If not connected to MongoDB
        """
        if self._collection is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        return self._collection

    @property
    def database(self) -> Database:
        """
        Get the MongoDB database.

        Returns:
            Database: MongoDB database instance

        Raises:
            RuntimeError: If not connected to MongoDB
        """
        if self._db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        return self._db

    def create_indexes(self) -> bool:
        """
        Create indexes on the procurement_orders collection for query performance.

        Indexes created:
        - creation_date (ASCENDING)
        - fiscal_year (ASCENDING)
        - department_name (ASCENDING)
        - supplier_name (ASCENDING)
        - item_name (TEXT) - for text search
        - total_price (DESCENDING)
        - Compound: (creation_date, fiscal_year)
        - Compound: (supplier_name, total_price)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            col = self.collection

            logger.info("Creating indexes on procurement_orders collection...")

            # Single field indexes
            col.create_index([("creation_date", ASCENDING)], name="idx_creation_date")
            logger.info("✓ Created index: creation_date")

            col.create_index([("fiscal_year", ASCENDING)], name="idx_fiscal_year")
            logger.info("✓ Created index: fiscal_year")

            col.create_index([("department_name", ASCENDING)], name="idx_department_name")
            logger.info("✓ Created index: department_name")

            col.create_index([("supplier_name", ASCENDING)], name="idx_supplier_name")
            logger.info("✓ Created index: supplier_name")

            col.create_index([("total_price", DESCENDING)], name="idx_total_price")
            logger.info("✓ Created index: total_price")

            # Text index for item_name (for text search)
            col.create_index([("item_name", TEXT)], name="idx_item_name_text")
            logger.info("✓ Created text index: item_name")

            # Compound indexes for common query patterns
            col.create_index(
                [("creation_date", ASCENDING), ("fiscal_year", ASCENDING)],
                name="idx_creation_date_fiscal_year"
            )
            logger.info("✓ Created compound index: creation_date + fiscal_year")

            col.create_index(
                [("supplier_name", ASCENDING), ("total_price", DESCENDING)],
                name="idx_supplier_name_total_price"
            )
            logger.info("✓ Created compound index: supplier_name + total_price")

            logger.info("All indexes created successfully!")
            return True

        except OperationFailure as e:
            logger.error(f"Failed to create indexes: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating indexes: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.

        Returns:
            Dict with collection statistics
        """
        try:
            col = self.collection

            # Get basic stats
            count = col.count_documents({})

            # Get date range
            oldest = col.find_one(sort=[("creation_date", ASCENDING)])
            newest = col.find_one(sort=[("creation_date", DESCENDING)])

            # Get spending stats
            total_spending_pipeline = [
                {"$group": {"_id": None, "total": {"$sum": "$total_price"}}}
            ]
            spending_result = list(col.aggregate(total_spending_pipeline))
            total_spending = spending_result[0]["total"] if spending_result else 0

            # Get unique counts
            unique_suppliers = len(col.distinct("supplier_name"))
            unique_departments = len(col.distinct("department_name"))
            unique_items = len(col.distinct("item_name"))

            return {
                "total_documents": count,
                "date_range": {
                    "oldest": oldest.get("creation_date") if oldest else None,
                    "newest": newest.get("creation_date") if newest else None,
                },
                "total_spending": total_spending,
                "unique_suppliers": unique_suppliers,
                "unique_departments": unique_departments,
                "unique_items": unique_items,
            }

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                "error": str(e)
            }

    def drop_collection(self) -> bool:
        """
        Drop the collection (use with caution!).

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.collection.drop()
            logger.warning(f"Collection '{self.collection_name}' dropped")
            return True
        except Exception as e:
            logger.error(f"Error dropping collection: {e}")
            return False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Convenience function for getting a connected client
def get_mongo_client(
    uri: str = config.MONGO_URI,
    db_name: str = config.MONGO_DB_NAME,
    collection_name: str = config.MONGO_COLLECTION
) -> MongoDBClient:
    """
    Get a connected MongoDB client.

    Args:
        uri: MongoDB connection URI
        db_name: Database name
        collection_name: Collection name

    Returns:
        MongoDBClient: Connected MongoDB client

    Raises:
        ConnectionError: If connection fails
    """
    client = MongoDBClient(uri, db_name, collection_name)
    if not client.connect():
        raise ConnectionError(f"Failed to connect to MongoDB at {uri}")
    return client
