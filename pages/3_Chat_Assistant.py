"""
Agentic Chat Assistant with Web Search - Shows reasoning loop iterations, tool usage, and web search.
"""
import streamlit as st
import logging
import json

from src.ai_agent_agentic import create_agentic_procurement_agent
import config

logger = logging.getLogger(__name__)


def log_chat_interaction(message_idx: int, feedback: str = "NA"):
    """
    Log a chat interaction to the configured destination.

    Args:
        message_idx: Index of the message in the messages list
        feedback: User feedback (upvote/downvote/NA)
    """
    if not st.session_state.logging_config.get("enabled"):
        return

    try:
        # Get the message and its corresponding user query
        messages = st.session_state.messages

        # Find the assistant message and its preceding user message
        if message_idx >= len(messages) or messages[message_idx].get("role") != "assistant":
            logger.warning(f"Invalid message index for logging: {message_idx}")
            return

        assistant_message = messages[message_idx]

        # Find the user query (should be right before the assistant message)
        user_query = ""
        for i in range(message_idx - 1, -1, -1):
            if messages[i].get("role") == "user":
                user_query = messages[i].get("content", "")
                break

        # Extract data
        query_data = assistant_message.get("query_data", {})
        tools_used = query_data.get("tools_used", [])
        response = assistant_message.get("content", "")
        model = st.session_state.llm_config.get("model", "unknown")
        token_count = query_data.get("token_count", {})

        # Log the interaction
        if st.session_state.chat_logger:
            st.session_state.chat_logger.log_interaction(
                session_id=st.session_state.session_id,
                model=model,
                user_query=user_query,
                tools_used=tools_used,
                response=response,
                user_feedback=feedback,
                token_count=token_count
            )

            logger.info(f"Logged interaction: message_idx={message_idx}, feedback={feedback}")

    except Exception as e:
        logger.error(f"Error logging chat interaction: {e}")


# Sample queries designed to show agentic capabilities + web search
SAMPLE_QUERIES = [
    # Database queries
    "How many total orders are in the database?",
    "Which quarter had the highest spending in fiscal year 2013-2014?",
    "What are the top 5 most frequently ordered items?",
    "Which department spent the most money?",  # This one shows the _id field observation
    "Who are the top 5 suppliers by revenue?",

    # Web search queries
    "What does UNSPSC stand for?",
    "What is the current inflation rate in California?",

    # Hybrid queries
    "Which department manages healthcare and what is the US healthcare budget?",
]


def initialize_agent():
    """Initialize the Agentic AI agent with web search if not already done."""
    if st.session_state.agent is None:
        if not st.session_state.mongo_client or not st.session_state.llm_manager:
            st.error("⚠️ Please complete configuration and data setup first")
            return False

        try:
            with st.spinner("Initializing Agentic AI agent (ReAct Loop + Web Search)..."):
                agent = create_agentic_procurement_agent(
                    mongo_client=st.session_state.mongo_client,
                    llm_manager=st.session_state.llm_manager,
                    use_few_shot=True,
                    enable_web_search=True  # Always enabled
                )
                st.session_state.agent = agent
                logger.info("✅ Agentic AI agent with web search initialized successfully")
                st.success("🤖 Agentic AI agent ready with 🌐 web search!")
                return True

        except Exception as e:
            st.error(f"Failed to initialize Agentic AI agent: {str(e)}")
            logger.error(f"Agent initialization error: {e}")
            return False

    return True


def render_sample_queries():
    """Render sample query buttons."""
    st.subheader("💡 Sample Queries")
    st.write("Click on a sample query to see the agent reason through it:")

    # Group queries
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 Database Queries**")
        for i, query in enumerate(SAMPLE_QUERIES[:5]):
            if st.button(query, key=f"sample_{i}", use_container_width=True):
                st.session_state.current_query = query
                st.rerun()

    with col2:
        st.markdown("**🌐 Web Search & Hybrid**")
        for i, query in enumerate(SAMPLE_QUERIES[5:], 5):
            if st.button(query, key=f"sample_{i}", use_container_width=True):
                st.session_state.current_query = query
                st.rerun()


def render_chat_message(role: str, content: str, query_data: dict = None, message_idx: int = None):
    """
    Render a chat message with optional query details.

    Args:
        role: "user" or "assistant"
        content: Message content
        query_data: Optional dict with query details (for assistant messages)
        message_idx: Message index for tracking feedback
    """
    with st.chat_message(role):
        st.markdown(content)

        if query_data and role == "assistant":
            # Show agentic details
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                iterations = query_data.get("iterations", 0)
                st.metric("🔄 Iterations", iterations)

            with col2:
                tools_used = query_data.get("tools_used", [])
                st.metric("🔧 Tools Used", len(tools_used))

            with col3:
                exec_time = query_data.get("execution_time", 0)
                st.metric("⏱️ Time", f"{exec_time:.2f}s")

            with col4:
                web_enabled = query_data.get("web_search_enabled", True)
                st.metric("🌐 Web", "On" if web_enabled else "Off")

            # Show detailed tool usage in expander
            if tools_used:
                with st.expander("🔍 View Agent's Reasoning Process"):
                    st.write("**Tools called by agent:**")
                    for i, tool in enumerate(tools_used, 1):
                        # Highlight web search calls
                        if tool == "search_web":
                            st.write(f"{i}. 🌐 `{tool}` ← Web search!")
                        else:
                            st.write(f"{i}. `{tool}`")

                    st.caption("The agent autonomously decided which tools to use and when.")

                    # Count web searches
                    web_search_count = tools_used.count('search_web')
                    if web_search_count > 0:
                        st.info(f"🌐 The agent performed {web_search_count} web search(es) to answer your question!")

            # Show token usage if available
            token_count = query_data.get("token_count", {})
            if token_count and token_count.get("total_token_count", 0) > 0:
                with st.expander("📊 Token Usage"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Input Tokens", f"{token_count.get('input_token_count', 0):,}")
                    with col2:
                        st.metric("Output Tokens", f"{token_count.get('output_token_count', 0):,}")
                    with col3:
                        st.metric("Total Tokens", f"{token_count.get('total_token_count', 0):,}")

            # Show any error details
            if query_data.get("error"):
                with st.expander("⚠️ Error Details"):
                    st.error(query_data["error"])

            # Feedback buttons (only if logging is enabled)
            if st.session_state.logging_config.get("enabled") and message_idx is not None:
                st.divider()
                st.caption("How was this answer?")

                # Initialize feedback storage if not exists
                if 'message_feedback' not in st.session_state:
                    st.session_state.message_feedback = {}

                col1, col2, col3 = st.columns([1, 1, 4])

                current_feedback = st.session_state.message_feedback.get(message_idx, "NA")

                with col1:
                    if st.button("👍", key=f"upvote_{message_idx}", help="Good answer"):
                        st.session_state.message_feedback[message_idx] = "upvote"
                        # Log the interaction
                        log_chat_interaction(message_idx, "upvote")
                        st.rerun()

                with col2:
                    if st.button("👎", key=f"downvote_{message_idx}", help="Poor answer"):
                        st.session_state.message_feedback[message_idx] = "downvote"
                        # Log the interaction
                        log_chat_interaction(message_idx, "downvote")
                        st.rerun()

                # Show current feedback status
                if current_feedback != "NA":
                    with col3:
                        feedback_text = "👍 Positive" if current_feedback == "upvote" else "👎 Negative"
                        st.caption(f"Feedback: {feedback_text}")


def process_query(user_query: str):
    """Process user query with agentic agent and display results."""
    if not st.session_state.agent:
        st.error("Agent not initialized")
        return

    try:
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": user_query
        })

        # Process query with agentic agent
        with st.spinner("🤖 Agent is reasoning..."):
            result = st.session_state.agent.process_query(user_query)

        if result["success"]:
            # Add assistant response to history
            message_idx = len(st.session_state.messages)
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["response"],
                "query_data": result
            })

            logger.info(
                f"Query processed successfully: {user_query} "
                f"(iterations: {result.get('iterations', 0)}, "
                f"tools: {result.get('tools_used', [])})"
            )

            # Auto-log the interaction with NA feedback (will be updated if user provides feedback)
            if st.session_state.logging_config.get("enabled"):
                log_chat_interaction(message_idx, "NA")

        else:
            # Show error
            error_msg = result.get("error", "Unknown error")
            st.error(f"Error processing query: {error_msg}")

            # Still add to messages for history
            st.session_state.messages.append({
                "role": "assistant",
                "content": result.get("response", "I encountered an error processing your query."),
                "query_data": result
            })

    except Exception as e:
        st.error(f"Error: {str(e)}")
        logger.error(f"Query processing error: {e}")


def main():
    """Main agentic chat assistant page with web search."""
    st.header("🤖 Agentic Chat Assistant")
    st.caption("**ReAct Loop + 🌐 Web Search** - Watch the agent reason, act, observe, and search the web!")

    # Check prerequisites
    if not st.session_state.llm_config:
        st.warning("⚠️ Please configure LLM provider first")
        if st.button("Go to Config"):
            st.switch_page("pages/1_Config.py")
        return

    if not st.session_state.mongo_connected or not st.session_state.data_loaded:
        st.warning("⚠️ Please complete data setup first")
        if st.button("Go to Data Setup"):
            st.switch_page("pages/2_Data_Setup.py")
        return

    # Initialize agent
    if not initialize_agent():
        return

    # Display data stats
    if st.session_state.data_stats:
        stats = st.session_state.data_stats
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_orders = stats.get("total_orders", 0)
            st.metric("Total Orders", f"{total_orders:,}")

        with col2:
            total_spending = stats.get("total_spending", 0)
            st.metric("Total Spending", f"${total_spending/1e9:.2f}B")

        with col3:
            unique_suppliers = stats.get("unique_suppliers", 0)
            st.metric("Suppliers", f"{unique_suppliers:,}")

        with col4:
            unique_departments = stats.get("unique_departments", 0)
            st.metric("Departments", f"{unique_departments:,}")

        st.divider()

    # Info box about agentic capabilities with web search
    with st.expander("ℹ️ About this Agentic Agent with Web Search"):
        st.markdown("""
**What makes this agent "agentic"?**

Unlike traditional chatbots that follow a fixed sequence, this agent uses a **ReAct Loop** (Reasoning + Acting):

1. **🧠 Thinks**: Analyzes your question and decides what to do
2. **🔧 Acts**: Calls tools autonomously:
   - `get_collection_schema`: Inspect database structure
   - `translate_query`: Convert natural language to MongoDB
   - `execute_mongodb_query`: Run queries
   - **`search_web`**: Search the internet for external information 🌐
3. **👀 Observes**: Examines the results
4. **🔄 Repeats**: If results look wrong, it can retry with a better query!

**New: Web Search Capability! 🌐**

The agent can now search the web for:
- ✅ Current events and news
- ✅ Definitions and acronyms
- ✅ General knowledge
- ✅ External data to complement procurement info

**Example Hybrid Query:**
"Which department manages healthcare and what is the US healthcare budget?"
- Agent queries MongoDB for California data
- Agent searches web for US budget info
- Agent combines both in the answer!

The agent **autonomously decides** when to use the database vs. web search.
        """)

    st.divider()

    # Sample queries
    render_sample_queries()

    st.divider()

    # Chat interface
    st.subheader("💬 Conversation")

    # Display chat history
    for idx, message in enumerate(st.session_state.messages):
        render_chat_message(
            role=message["role"],
            content=message["content"],
            query_data=message.get("query_data"),
            message_idx=idx
        )

    # Process current query if set
    if st.session_state.current_query:
        query = st.session_state.current_query
        st.session_state.current_query = ""  # Clear
        process_query(query)
        st.rerun()

    # Chat input
    user_input = st.chat_input("Ask me anything about procurement data... or the world! 🌐")

    if user_input:
        process_query(user_input)
        st.rerun()

    # Clear conversation button
    if st.session_state.messages:
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.messages = []
                if st.session_state.agent:
                    st.session_state.agent.clear_history()
                st.rerun()

        with col2:
            # Export conversation
            if st.button("💾 Export Chat", use_container_width=True):
                import json
                from datetime import datetime

                export_data = {
                    "exported_at": datetime.now().isoformat(),
                    "agent_type": "Agentic ReAct Loop",
                    "messages": st.session_state.messages
                }

                st.download_button(
                    label="Download JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"agentic_chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )


if __name__ == "__main__":
    main()
