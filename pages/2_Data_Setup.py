"""
Data setup page for loading procurement data into MongoDB.
"""
import streamlit as st
import logging
from pathlib import Path

from src.mongo_client import get_mongo_client, MongoDBClient
from src.data_loader import load_procurement_data
import config

logger = logging.getLogger(__name__)


def render_mongodb_config():
    """Render MongoDB configuration."""
    st.subheader("MongoDB Configuration")

    col1, col2 = st.columns(2)

    with col1:
        mongo_uri = st.text_input(
            "MongoDB URI",
            value=config.MONGO_URI,
            help="MongoDB connection string"
        )

    with col2:
        db_name = st.text_input(
            "Database Name",
            value=config.MONGO_DB_NAME,
            help="Name of the database to use"
        )

    collection_name = st.text_input(
        "Collection Name",
        value=config.MONGO_COLLECTION,
        help="Name of the collection for procurement data"
    )

    return {
        "uri": mongo_uri,
        "db_name": db_name,
        "collection_name": collection_name
    }


def test_mongo_connection(mongo_config):
    """Test MongoDB connection."""
    try:
        with st.spinner("Testing MongoDB connection..."):
            mongo_client = get_mongo_client(
                uri=mongo_config["uri"],
                db_name=mongo_config["db_name"],
                collection_name=mongo_config["collection_name"]
            )

            st.success("✓ MongoDB connection successful!")

            # Check if data already exists
            count = mongo_client.collection.count_documents({})
            if count > 0:
                st.info(f"Database already contains {count:,} documents")

            return mongo_client

    except Exception as e:
        st.error(f"✗ MongoDB connection failed: {str(e)}")
        logger.error(f"MongoDB connection error: {e}")
        return None


def load_data_to_mongo(mongo_client: MongoDBClient):
    """Load CSV data into MongoDB."""
    try:
        # Check if data already loaded
        existing_count = mongo_client.collection.count_documents({})
        if existing_count > 0:
            st.warning(f"⚠️ Database already contains {existing_count:,} documents.")
            if not st.checkbox("Clear existing data and reload?"):
                st.info("Skipping data load. Using existing data.")
                st.session_state.data_loaded = True
                st.session_state.data_stats = mongo_client.get_collection_stats()
                return True

            # Drop existing collection
            with st.spinner("Clearing existing data..."):
                mongo_client.drop_collection()
                st.success("✓ Existing data cleared")

        # Create progress placeholders
        progress_bar = st.progress(0)
        status_text = st.empty()
        stats_placeholder = st.empty()

        # Define progress callback
        def progress_callback(current, total):
            progress = current / total
            progress_bar.progress(progress)
            status_text.text(f"Loading: {current:,} / {total:,} rows ({progress*100:.1f}%)")

        # Load data
        status_text.text("Starting data load...")

        stats = load_procurement_data(
            mongo_client=mongo_client,
            csv_path=config.CSV_FILE,
            batch_size=config.DATA_LOAD_BATCH_SIZE,
            progress_callback=progress_callback
        )

        # Update progress
        progress_bar.progress(1.0)
        status_text.text("Data load complete!")

        # Display statistics
        with stats_placeholder.container():
            st.success("✓ Data loaded successfully!")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows Processed", f"{stats['total_rows_processed']:,}")
            with col2:
                st.metric("Rows Inserted", f"{stats['total_rows_inserted']:,}")
            with col3:
                st.metric("Rows Skipped", f"{stats['total_rows_skipped']:,}")

            if stats.get("errors"):
                with st.expander("View Errors"):
                    st.write(stats["errors"])

        # Get collection statistics
        collection_stats = mongo_client.get_collection_stats()
        st.session_state.data_stats = collection_stats
        st.session_state.data_loaded = True

        return True

    except FileNotFoundError as e:
        st.error(f"✗ CSV file not found: {str(e)}")
        st.info(f"Expected file at: {config.CSV_FILE}")
        return False

    except Exception as e:
        st.error(f"✗ Error loading data: {str(e)}")
        logger.error(f"Data loading error: {e}")
        return False


def display_data_statistics():
    """Display data statistics."""
    if not st.session_state.data_stats:
        return

    stats = st.session_state.data_stats

    st.subheader("📊 Data Statistics")

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Orders", f"{stats.get('total_documents', 0):,}")

    with col2:
        total_spending = stats.get('total_spending', 0)
        st.metric("Total Spending", f"${total_spending:,.2f}")

    with col3:
        st.metric("Unique Suppliers", f"{stats.get('unique_suppliers', 0):,}")

    with col4:
        st.metric("Unique Departments", f"{stats.get('unique_departments', 0):,}")

    # Date range
    date_range = stats.get('date_range', {})
    if date_range.get('oldest') and date_range.get('newest'):
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Oldest Order:** {date_range['oldest']}")
        with col2:
            st.info(f"**Newest Order:** {date_range['newest']}")


def main():
    """Main data setup page."""
    st.header("📂 Data Setup")

    st.write(
        "Configure MongoDB connection and load the procurement data. "
        "The CSV file will be loaded in batches for optimal performance."
    )

    # MongoDB configuration
    mongo_config = render_mongodb_config()

    st.divider()

    # Test connection
    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("🔌 Connect to MongoDB", use_container_width=True):
            mongo_client = test_mongo_connection(mongo_config)

            if mongo_client:
                st.session_state.mongo_client = mongo_client
                st.session_state.mongo_connected = True

                # Check if data already loaded
                count = mongo_client.collection.count_documents({})
                if count > 0:
                    st.session_state.data_loaded = True
                    st.session_state.data_stats = mongo_client.get_collection_stats()

    # Data loading section
    if st.session_state.mongo_connected:
        st.divider()

        # Display CSV file info
        csv_file = config.CSV_FILE
        if csv_file.exists():
            file_size_mb = csv_file.stat().st_size / (1024 * 1024)
            st.info(f"**CSV File:** {csv_file.name} ({file_size_mb:.1f} MB)")
        else:
            st.error(f"⚠️ CSV file not found at: {csv_file}")

        # Load data button
        if st.button("⬇️ Load Data to MongoDB", use_container_width=True):
            if st.session_state.mongo_client:
                load_data_to_mongo(st.session_state.mongo_client)
            else:
                st.error("Please connect to MongoDB first")

        # Display statistics if data loaded
        if st.session_state.data_loaded:
            st.divider()
            display_data_statistics()

    # Navigation
    st.divider()

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("← Back: Config", use_container_width=True):
            st.switch_page("pages/1_Config.py")

    with col2:
        next_disabled = not (st.session_state.mongo_connected and st.session_state.data_loaded)

        if st.button(
            "Next: Chat Assistant →",
            disabled=next_disabled,
            use_container_width=True,
            help="Connect to MongoDB and load data first" if next_disabled else "Go to chat assistant"
        ):
            st.switch_page("pages/3_Chat_Assistant.py")

    if next_disabled:
        if not st.session_state.mongo_connected:
            st.warning("⚠️ Please connect to MongoDB before proceeding.")
        elif not st.session_state.data_loaded:
            st.warning("⚠️ Please load data before proceeding.")


if __name__ == "__main__":
    main()
