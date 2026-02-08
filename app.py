"""
Main Streamlit application for AI-Powered Procurement Assistant.
Entry point for the multi-page app.
"""
import streamlit as st
import logging

import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)

logger = logging.getLogger(__name__)


def init_session_state():
    """Initialize session state variables."""
    # LLM Configuration
    if 'llm_config' not in st.session_state:
        st.session_state.llm_config = None

    if 'llm_manager' not in st.session_state:
        st.session_state.llm_manager = None

    # MongoDB Connection
    if 'mongo_client' not in st.session_state:
        st.session_state.mongo_client = None

    if 'mongo_connected' not in st.session_state:
        st.session_state.mongo_connected = False

    # Data Loading
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False

    if 'data_stats' not in st.session_state:
        st.session_state.data_stats = None

    # AI Agent
    if 'agent' not in st.session_state:
        st.session_state.agent = None

    # Chat Messages
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # UI State
    if 'current_query' not in st.session_state:
        st.session_state.current_query = ""

    # Logging
    if 'logging_config' not in st.session_state:
        st.session_state.logging_config = {"enabled": False}

    if 'chat_logger' not in st.session_state:
        st.session_state.chat_logger = None

    if 'session_id' not in st.session_state:
        from src.chat_logger import ChatLogger
        st.session_state.session_id = ChatLogger.generate_session_id()


def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.APP_ICON,
        layout=config.APP_LAYOUT,
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    init_session_state()

    # Main title
    st.title(f"{config.APP_ICON} {config.APP_TITLE}")
    st.caption("🤖 Powered by Agentic AI with ReAct Loop")

    # Sidebar
    with st.sidebar:
        st.header("📊 Status")

        if st.session_state.llm_config:
            provider = st.session_state.llm_config.get("provider", "None")
            st.success(f"✓ LLM: {provider}")
        else:
            st.warning("⚠ LLM: Not configured")

        if st.session_state.mongo_connected:
            st.success("✓ MongoDB: Connected")
        else:
            st.warning("⚠ MongoDB: Not connected")

        if st.session_state.data_loaded:
            if st.session_state.data_stats:
                count = st.session_state.data_stats.get("total_documents", 0)
                st.success(f"✓ Data: {count:,} records")
            else:
                st.success("✓ Data: Loaded")
        else:
            st.warning("⚠ Data: Not loaded")

        st.divider()

        # Global actions
        if st.button("🔄 Reset All", help="Clear all settings and data", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Welcome section
    st.markdown("""
    ### Welcome! 👋

    This AI-powered assistant helps you analyze **California state procurement data** (2012-2015)
    using natural language queries. The agent uses a **ReAct Loop** (Reasoning + Acting) to:

    - 🧠 **Think** - Analyze your question
    - 🔧 **Act** - Call tools (schema inspection, query translation, execution)
    - 👀 **Observe** - Examine results
    - 🔄 **Repeat** - Retry if needed

    ### Get Started in 3 Steps:
    """)

    # Navigation cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 1️⃣ Configure")
        st.markdown("Set up your LLM provider (Gemini or GPT)")
        if st.button("→ Go to Config", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Config.py")

    with col2:
        st.markdown("#### 2️⃣ Load Data")
        st.markdown("Connect to MongoDB and load procurement data")
        if st.button("→ Go to Data Setup", use_container_width=True, type="primary"):
            st.switch_page("pages/2_Data_Setup.py")

    with col3:
        st.markdown("#### 3️⃣ Chat")
        st.markdown("Ask questions in natural language")
        if st.button("→ Go to Chat Assistant", use_container_width=True, type="primary"):
            st.switch_page("pages/3_Chat_Assistant.py")

    # Additional info
    st.divider()

    with st.expander("ℹ️ About the Agentic AI"):
        st.markdown("""
        **What makes this agent "agentic"?**

        Unlike traditional chatbots with fixed workflows, this agent:
        - ✅ Can inspect the database schema when unsure about field names
        - ✅ Observes query results and retries if something looks wrong
        - ✅ Formats responses naturally based on what it sees
        - ✅ Preserves ALL data including MongoDB `_id` fields

        **Example:** When asked "Which department spent the most?", the agent:
        1. Generates an aggregation query
        2. Executes it and sees: `{"_id": "Transportation", "total": 99000000000}`
        3. Notices the department name is in the `_id` field
        4. Responds: "**Transportation** spent $99 billion" (not just "$99 billion")
        """)

    st.divider()
    st.caption("Use the sidebar to track your setup progress →")


if __name__ == "__main__":
    main()
