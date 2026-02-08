"""
Configuration page V2 - Enhanced OpenAI support with auto-population from .env
"""
import streamlit as st
import logging
import os

from src.llm_manager import LLMManagerV2 as LLMManager, create_llm_manager_v2 as create_llm_manager
import config

logger = logging.getLogger(__name__)


def render_gemini_config():
    """Render Gemini configuration options."""
    st.subheader("🔷 Gemini Configuration")

    # Get API key from multiple sources
    default_api_key = (
        os.getenv("GOOGLE_API_KEY") or
        os.getenv("GOOGLE_CLOUD_API_KEY") or
        config.GEMINI_API_KEY or
        ""
    )

    if default_api_key:
        st.success(f"✓ API key detected from environment (starts with: {default_api_key[:10]}...)")
    else:
        st.info("💡 Enter your Gemini API key below, or set GOOGLE_API_KEY environment variable")

    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        value=default_api_key,
        help="Get your key from: https://makersuite.google.com/app/apikey"
    )

    model = st.selectbox(
        "Gemini Model",
        options=[
            "gemini-3-pro-preview",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ],
        index=0 if config.GEMINI_MODEL == "gemini-3-pro-preview" else
              (1 if config.GEMINI_MODEL == "gemini-2.0-flash-exp" else 2),
        help="Select the Gemini model to use"
    )

    # Service Account (advanced)
    sa_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    with st.expander("🔧 Advanced: Service Account (Fallback)", expanded=False):
        if sa_key_path:
            st.success(f"✓ Service Account detected: `{os.path.basename(sa_key_path)}`")
            st.info("Will be used as fallback if API key is not provided.")
        else:
            st.info("No service account configured. Using API key mode only.")

    return {
        "use_adc": bool(sa_key_path),
        "vertex_project": config.VERTEX_PROJECT,
        "vertex_location": "global",
        "model": model,
        "api_key": api_key
    }


def render_openai_config():
    """Render OpenAI configuration options with auto-population."""
    st.subheader("🤖 OpenAI Configuration")

    # Get API key from environment
    default_api_key = config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY") or ""

    if default_api_key:
        # Mask the key for security
        masked_key = f"{default_api_key[:7]}...{default_api_key[-4:]}" if len(default_api_key) > 11 else default_api_key[:7] + "..."
        st.success(f"✓ API key detected from environment: {masked_key}")
    else:
        st.info("💡 Enter your OpenAI API key below, or set OPENAI_API_KEY environment variable")

    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=default_api_key,
        help="Your OpenAI API key (starts with sk-)"
    )

    col1, col2 = st.columns(2)

    with col1:
        # Get default model from config
        default_model = config.OPENAI_MODEL
        available_models = [
            "gpt-5",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ]

        # Find index of default model
        try:
            default_index = available_models.index(default_model)
        except ValueError:
            default_index = 1  # Default to gpt-4o-mini

        model = st.selectbox(
            "OpenAI Model",
            options=available_models,
            index=default_index,
            help="Select the OpenAI model to use"
        )

    with col2:
        org_id = st.text_input(
            "Organization ID (Optional)",
            value=config.OPENAI_ORG_ID,
            help="Your OpenAI organization ID (if applicable)"
        )

    # Show estimated cost info
    with st.expander("💰 Estimated Costs", expanded=False):
        if model == "gpt-5":
            st.warning("**gpt-5:** Premium model - Pricing TBA by OpenAI")
        elif model == "gpt-4o":
            st.info("**gpt-4o:** $2.50/1M input tokens, $10.00/1M output tokens")
        elif model == "gpt-4o-mini":
            st.success("**gpt-4o-mini:** $0.15/1M input tokens, $0.60/1M output tokens (Recommended for cost)")
        elif model == "gpt-4-turbo":
            st.info("**gpt-4-turbo:** $10.00/1M input tokens, $30.00/1M output tokens")
        elif model == "gpt-3.5-turbo":
            st.success("**gpt-3.5-turbo:** $0.50/1M input tokens, $1.50/1M output tokens")

    return {
        "api_key": api_key,
        "model": model,
        "organization": org_id if org_id else None
    }


def test_llm_connection(provider, config_data):
    """Test LLM connection using V2 manager."""
    try:
        # Validate authentication
        if provider == "Gemini":
            api_key = config_data.get("api_key")
            sa_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

            if not api_key and not sa_key_path:
                st.error("⚠️ Please provide a Gemini API key or configure GOOGLE_APPLICATION_CREDENTIALS")
                return None

            if api_key:
                if api_key.startswith("AQ."):
                    st.info("🔑 Using Vertex AI Express Mode API key")
                else:
                    st.info("🔑 Using Gemini Developer API key")
            elif sa_key_path:
                st.info(f"🔐 Using Service Account: {os.path.basename(sa_key_path)}")

        elif provider == "OpenAI":
            if not config_data.get("api_key"):
                st.error("⚠️ Please enter your OpenAI API key")
                return None

        with st.spinner(f"Testing {provider} connection..."):
            if provider == "Gemini":
                llm_manager = create_llm_manager(
                    provider="gemini",
                    api_key=config_data.get("api_key"),
                    use_adc=config_data.get("use_adc", False),
                    model=config_data.get("model"),
                    vertex_project=config_data.get("vertex_project"),
                    vertex_location=config_data.get("vertex_location")
                )
            else:  # OpenAI
                llm_manager = create_llm_manager(
                    provider="openai",
                    api_key=config_data["api_key"],
                    model=config_data.get("model"),
                    organization=config_data.get("organization")
                )

            # Test connection
            test_result = llm_manager.test_connection()

            if test_result["success"]:
                st.success(f"✓ {provider} connection successful!")
                st.info(f"**Model:** {test_result['model']}")
                st.caption(f"**Response:** {test_result['response']}")
                return llm_manager
            else:
                st.error(f"✗ {provider} connection failed: {test_result.get('error', 'Unknown error')}")
                with st.expander("Error Details"):
                    st.code(test_result.get('error', 'Unknown error'))
                return None

    except Exception as e:
        st.error(f"✗ Error testing {provider} connection: {str(e)}")
        logger.error(f"Error testing {provider}: {e}", exc_info=True)
        with st.expander("Error Details"):
            st.code(str(e))
        return None


def main():
    """Main configuration page."""
    st.header("⚙️ LLM Configuration")

    st.markdown("""
    Configure your Language Model provider. Choose between:
    - **Gemini**: Google's latest models (3-pro-preview, 2.0-flash-exp, etc.)
    - **OpenAI**: GPT-4o, GPT-4o-mini, and other ChatGPT models
    """)

    st.divider()

    # Provider selection
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        provider = st.selectbox(
            "Provider",
            options=["Gemini", "OpenAI"],
            index=0,
            help="Select your preferred LLM provider"
        )

    # Provider-specific configuration
    st.divider()

    if provider == "Gemini":
        config_data = render_gemini_config()
    else:
        config_data = render_openai_config()

    # Logging Configuration
    st.divider()
    st.subheader("📊 Chat Logging Configuration")

    logging_enabled = st.checkbox(
        "Enable Chat Logging",
        value=False,
        help="Log all chat interactions for analysis and feedback"
    )

    logging_config = {"enabled": logging_enabled}

    if logging_enabled:
        col1, col2 = st.columns(2)

        with col1:
            log_destination = st.radio(
                "Logging Destination",
                options=["Local CSV", "BigQuery"],
                index=0,
                help="Choose where to store chat logs"
            )

            logging_config["log_to_bigquery"] = (log_destination == "BigQuery")

        with col2:
            if log_destination == "BigQuery":
                use_default_table = st.checkbox(
                    "Use Default Table",
                    value=True,
                    help=f"Default: hudhud-demo.penny_demo.chat_logs"
                )

                logging_config["use_default_table"] = use_default_table

                if not use_default_table:
                    st.text_input("Custom Project", value="hudhud-demo", key="custom_project")
                    st.text_input("Custom Dataset", value="penny_demo", key="custom_dataset")
                    st.text_input("Custom Table", value="chat_logs", key="custom_table")
                    logging_config["custom_project"] = st.session_state.get("custom_project")
                    logging_config["custom_dataset"] = st.session_state.get("custom_dataset")
                    logging_config["custom_table"] = st.session_state.get("custom_table")
            else:
                csv_path = st.text_input(
                    "CSV File Path",
                    value="chat_logs.csv",
                    help="Path to local CSV file (will be created if doesn't exist)"
                )
                logging_config["local_csv_path"] = csv_path

        # Info about logging
        with st.expander("ℹ️ What gets logged?"):
            st.markdown("""
            Each chat interaction logs:
            - **Session ID** - Unique identifier for the session
            - **Timestamp** - When the interaction occurred
            - **Model** - Which LLM model was used
            - **User Query** - The question asked
            - **Tools Used** - Which agent tools were called
            - **Response** - The agent's answer
            - **User Feedback** - Upvote/downvote/NA

            **Note:** If BigQuery logging fails, logs will automatically fallback to local CSV.
            """)

    # Test and save configuration
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("🧪 Test Connection", use_container_width=True, type="primary"):
            llm_manager = test_llm_connection(provider, config_data)

            if llm_manager:
                # Save to session state
                st.session_state.llm_manager = llm_manager
                st.session_state.llm_config = {
                    "provider": provider,
                    **config_data
                }
                st.session_state.logging_config = logging_config

                # Initialize chat logger
                from src.chat_logger import create_chat_logger

                # Debug: Show what we're passing to the logger
                logger.info(f"Creating chat logger with config: {logging_config}")

                st.session_state.chat_logger = create_chat_logger(**logging_config)

                st.success("✅ Configuration saved to session!")
                if logging_enabled:
                    destination = "BigQuery" if logging_config.get("log_to_bigquery") else "Local CSV"
                    st.info(f"📊 Chat logging enabled → {destination}")

                    # Debug: Show logger state
                    if st.session_state.chat_logger:
                        logger.info(f"ChatLogger state: enabled={st.session_state.chat_logger.enabled}, "
                                  f"log_to_bigquery={st.session_state.chat_logger.log_to_bigquery}, "
                                  f"bq_available={st.session_state.chat_logger.bq_available}")

    # Navigation
    st.divider()

    col1, col2 = st.columns([1, 1])

    with col2:
        next_disabled = st.session_state.llm_config is None

        if st.button(
            "Next: Data Setup →",
            disabled=next_disabled,
            use_container_width=True,
            help="Configure LLM first" if next_disabled else "Go to data setup"
        ):
            st.switch_page("pages/2_Data_Setup.py")

    if next_disabled:
        st.warning("⚠️ Please test your LLM connection before proceeding.")
    else:
        # Show current configuration
        with st.expander("📋 Current Configuration"):
            st.json(st.session_state.llm_config)


if __name__ == "__main__":
    main()
