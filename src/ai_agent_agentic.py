"""
Truly Agentic AI Procurement Agent - ReAct Loop Implementation
Uses Reasoning -> Acting -> Observing loop for intelligent query processing.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback
import json

import os
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from google.oauth2 import service_account

from src.mongo_client import MongoDBClient
from src.llm_manager import LLMManager
from src.query_translator_langchain import create_langchain_query_translator
import config

logger = logging.getLogger(__name__)


class AgenticProcurementAgent:
    """
    Truly Agentic Procurement Assistant using ReAct Loop.

    Key Differences from Chain-based Agent:
    1. Agent can OBSERVE results and RETRY if needed
    2. Agent can DECIDE which tools to use dynamically
    3. Agent can INSPECT schema if confused about fields
    4. Agent FORMATS its own responses naturally
    """

    def __init__(
        self,
        mongo_client: MongoDBClient,
        llm_manager: LLMManager,
        use_few_shot: bool = True,
        enable_web_search: bool = True
    ):
        """
        Initialize Agentic Procurement Agent.

        Args:
            mongo_client: MongoDB client instance
            llm_manager: LLM manager instance
            use_few_shot: Whether to use few-shot examples
            enable_web_search: Whether to enable web search tool (default: True)
        """
        self.mongo = mongo_client
        self.llm_manager = llm_manager
        self.use_few_shot = use_few_shot
        self.enable_web_search = enable_web_search

        # Create LangChain LLM
        self.llm = self._create_langchain_llm()

        # Create query translator (for translate_query tool)
        self.translator = create_langchain_query_translator(
            llm_manager,
            num_examples=5 if use_few_shot else 0
        )

        # Create custom tools (including schema inspection and web search!)
        self.tools = self._create_tools()

        # Bind tools to LLM (enable tool calling)
        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # Conversation history (manual tracking)
        self.conversation_history = []

    def _create_langchain_llm(self):
        """Create LangChain LLM instance."""
        provider = self.llm_manager.provider

        # Normalize provider name
        if provider == "openai":
            provider = "gpt"  # Backwards compatibility

        if provider == "gemini":
            # Default: Use API key mode
            api_key = self.llm_manager.api_key or config.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY")

            if api_key:
                # Check if this is a Vertex AI Express Mode key (starts with AQ.)
                # or standard Developer API key (starts with AIzaSy)
                if api_key.startswith("AQ."):
                    logger.info("Using Vertex AI Express Mode with API key - Agentic Agent")
                    # For Vertex AI Express Mode, use vertexai=True but NO project/location
                    return ChatGoogleGenerativeAI(
                        model=self.llm_manager.model,
                        temperature=config.DEFAULT_TEMPERATURE,
                        max_tokens=config.DEFAULT_MAX_TOKENS,
                        google_api_key=api_key,
                        vertexai=True,  # Required for Vertex AI Express Mode
                        convert_system_message_to_human=True
                    )
                else:
                    logger.info("Using Gemini Developer API with API key - Agentic Agent")
                    return ChatGoogleGenerativeAI(
                        model=self.llm_manager.model,
                        temperature=config.DEFAULT_TEMPERATURE,
                        max_tokens=config.DEFAULT_MAX_TOKENS,
                        google_api_key=api_key,
                        convert_system_message_to_human=True
                    )

            # Fallback: Check if using Service Account
            sa_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if sa_key_path:
                logger.info(f"Using Vertex AI with Service Account: {sa_key_path}")
                credentials = service_account.Credentials.from_service_account_file(
                    sa_key_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                return ChatGoogleGenerativeAI(
                    model=self.llm_manager.model,
                    temperature=config.DEFAULT_TEMPERATURE,
                    max_tokens=config.DEFAULT_MAX_TOKENS,
                    credentials=credentials,
                    project=self.llm_manager.vertex_project,
                    location=self.llm_manager.vertex_location,
                    vertexai=True,
                    convert_system_message_to_human=True
                )

            raise ValueError(
                "Gemini authentication required. "
                "Please provide API key (GOOGLE_API_KEY) or configure service account (GOOGLE_APPLICATION_CREDENTIALS)."
            )

        elif provider == "gpt":
            return ChatOpenAI(
                model=self.llm_manager.model,
                temperature=config.DEFAULT_TEMPERATURE,
                max_tokens=config.DEFAULT_MAX_TOKENS,
                api_key=self.llm_manager.api_key
            )

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _create_tools(self):
        """
        Create custom LangChain tools including Schema Inspection and Web Search.

        Returns:
            List of tool functions
        """

        @tool
        def get_collection_schema() -> str:
            """
            Returns the schema/sample document of the procurement collection.
            Useful for checking field names (e.g., 'total_price' vs 'unit_cost')
            or understanding what data is available.

            Returns:
                String describing collection fields and a sample document
            """
            try:
                # Get a single document to show structure
                sample = self.mongo.collection.find_one()
                if not sample:
                    return "Collection is empty."

                # Extract field names
                keys = list(sample.keys())

                # Create a clean representation
                fields_list = ", ".join([k for k in keys if k != "_id"])

                # Sample values for key fields
                sample_clean = {k: v for k, v in sample.items() if k in [
                    "department_name", "supplier_name", "item_name",
                    "total_price", "fiscal_year", "fiscal_quarter",
                    "creation_date", "quantity"
                ]}

                return f"""Collection Fields: {fields_list}

Sample Document:
{json.dumps(sample_clean, indent=2, default=str)}

Key Field Notes:
- Dates: creation_date (string MM/DD/YYYY), fiscal_year (string "2013-2014"), fiscal_quarter (Q1-Q4)
- Money: total_price (number), unit_price (number)
- Identifiers: department_name, supplier_name, item_name
- Grouping: Use fiscal_year and fiscal_quarter for time-based queries
"""
            except Exception as e:
                logger.error(f"Error getting schema: {e}")
                return f"Error retrieving schema: {str(e)}"

        @tool
        def translate_query(user_question: str) -> str:
            """
            Translates a natural language question about procurement data into a MongoDB query.

            Args:
                user_question: Natural language question about procurement data

            Returns:
                JSON string with query_type, query, and explanation
            """
            return self._tool_translate_query(user_question)

        @tool
        def execute_mongodb_query(query_json: str) -> str:
            """
            Executes a MongoDB query and returns results.

            Args:
                query_json: JSON string with 'query_type' (find or aggregate) and 'query'

            Returns:
                JSON string with query results
            """
            return self._tool_execute_query(query_json)

        @tool
        def search_web(query: str, max_results: int = 5) -> str:
            """
            Search the web for information using DuckDuckGo.
            Useful for finding external information not available in the procurement database,
            such as current events, definitions, or general knowledge.

            Args:
                query: Search query string
                max_results: Maximum number of results to return (default: 5)

            Returns:
                JSON string with search results including titles, snippets, and URLs
            """
            return self._tool_search_web(query, max_results)

        # NOTE: We REMOVED 'format_response' tool
        # The Agent is smart enough to format the final answer itself
        # once it sees the data in the conversation history

        # Build tools list
        tools = [get_collection_schema, translate_query, execute_mongodb_query]

        if self.enable_web_search:
            tools.append(search_web)
            logger.info("✓ Web search tool enabled")

        return tools

    def _tool_translate_query(self, user_question: str) -> str:
        """Tool function: Translate natural language to MongoDB query."""
        try:
            result = self.translator.translate(user_question)
            logger.debug(f"Translation result type: {type(result)}, value: {str(result)[:200]}")
            json_result = json.dumps(result)
            logger.debug(f"JSON serialized result: {json_result[:200]}")
            return json_result
        except Exception as e:
            logger.error(f"Translation error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return json.dumps({"error": str(e)})

    def _tool_execute_query(self, query_json: str) -> str:
        """Tool function: Execute MongoDB query."""
        try:
            logger.info(f"Executing query, received JSON: {query_json[:500]}")
            query_data = json.loads(query_json)
            logger.info(f"Parsed query_data type: {type(query_data)}")

            # Handle case where query_data might be a list or not have expected structure
            if isinstance(query_data, list):
                logger.error(f"query_data is unexpectedly a list: {query_data}")
                return json.dumps({
                    "success": False,
                    "error": "Query translation returned a list instead of dict. Expected {query_type, query, explanation}.",
                    "results": [],
                    "count": 0
                })

            if "query_type" not in query_data:
                logger.error(f"query_data missing 'query_type': {query_data}")
                return json.dumps({
                    "success": False,
                    "error": f"Missing 'query_type' in query data. Got keys: {list(query_data.keys()) if isinstance(query_data, dict) else 'not a dict'}",
                    "results": [],
                    "count": 0
                })

            query_type = query_data["query_type"]
            query = query_data["query"]
            logger.info(f"Extracted query_type={query_type}, query type={type(query)}")

            # Handle case where agent passes pipeline array directly instead of {"pipeline": [...]}
            if query_type == "aggregate" and isinstance(query, list):
                logger.warning(f"Agent passed pipeline array directly, wrapping it in dict")
                query = {"pipeline": query}

            # Validate query structure
            if not isinstance(query, dict):
                logger.error(f"query should be a dict but got {type(query)}: {query}")
                return json.dumps({
                    "success": False,
                    "error": f"Invalid query structure. Expected dict with 'filter' or 'pipeline', got {type(query).__name__}",
                    "results": [],
                    "count": 0
                })

            collection = self.mongo.collection

            if query_type == "find":
                filter_dict = query.get("filter", {})
                limit = query.get("limit", config.MAX_QUERY_RESULTS)

                cursor = collection.find(filter_dict).limit(limit)
                results = list(cursor)

            elif query_type == "aggregate":
                pipeline = query.get("pipeline", [])

                # Add limit if not present
                has_limit = any("$limit" in stage for stage in pipeline)
                if not has_limit and not any("$count" in stage for stage in pipeline):
                    pipeline.append({"$limit": config.MAX_QUERY_RESULTS})

                cursor = collection.aggregate(
                    pipeline,
                    maxTimeMS=config.QUERY_TIMEOUT_SECONDS * 1000
                )
                results = list(cursor)

            else:
                raise ValueError(f"Unsupported query type: {query_type}")

            # Serialize results (convert ObjectId and datetime)
            results = self._serialize_results(results)

            return json.dumps({
                "success": True,
                "results": results,
                "count": len(results)
            })

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "results": [],
                "count": 0
            })

    def _serialize_results(self, results: List[Dict]) -> List[Dict]:
        """
        Serialize MongoDB results - KEEPS ALL FIELDS including _id!

        CRITICAL: The _id field often contains the grouped-by value in aggregations,
        so we MUST preserve it for the agent to see.
        """
        from bson import ObjectId

        serialized = []
        for doc in results:
            serialized_doc = {}
            for key, value in doc.items():
                # KEEP _id and all other fields!
                if isinstance(value, ObjectId):
                    serialized_doc[key] = str(value)
                elif isinstance(value, datetime):
                    serialized_doc[key] = value.isoformat()
                else:
                    serialized_doc[key] = value
            serialized.append(serialized_doc)

        logger.debug(f"Serialized {len(serialized)} results, sample: {serialized[0] if serialized else 'none'}")
        return serialized

    def _tool_search_web(self, query: str, max_results: int = 5) -> str:
        """Tool function: Search the web using DuckDuckGo via LangChain."""
        try:
            from langchain_community.tools import DuckDuckGoSearchResults

            logger.info(f"Searching web for: {query}")

            # Use LangChain's DuckDuckGo search tool
            search = DuckDuckGoSearchResults(num_results=max_results)
            results_str = search.invoke(query)

            logger.info(f"Web search completed, raw results: {results_str[:200]}...")

            # LangChain returns results as a string, parse it
            # Format: [snippet: ..., title: ..., link: ...]
            return json.dumps({
                "success": True,
                "query": query,
                "results": results_str,
                "count": max_results
            })

        except Exception as e:
            logger.error(f"Web search error: {e}")
            return json.dumps({
                "success": False,
                "error": str(e),
                "query": query,
                "results": "",
                "count": 0
            })

    def process_query(self, user_question: str) -> Dict[str, Any]:
        """
        True Agentic Loop with Web Search: Reason -> Act -> Observe -> Repeat

        The agent can:
        1. Inspect schema if unsure about field names
        2. Translate queries
        3. Execute queries
        4. SEARCH THE WEB for external information
        5. OBSERVE results and retry if wrong
        6. Format its own natural language response

        Args:
            user_question: User's natural language question

        Returns:
            Dict with results and metadata
        """
        start_time = datetime.now()

        # Initialize token counters
        total_input_tokens = 0
        total_output_tokens = 0

        # Build web search section for system prompt
        web_search_section = """
4. **search_web**: Search the internet for external information
   - Use this when the user asks about current events, definitions, or general knowledge
   - NOT for procurement data queries (use translate_query + execute_mongodb_query for that)
   - Example: "What is the inflation rate in 2023?" -> use search_web
   - Example: "What does UNSPSC mean?" -> use search_web
""" if self.enable_web_search else ""

        # System Prompt: Defines the Agent's Persona and Strategy
        system_prompt = f"""You are an expert Procurement Data Agent for California state procurement data.
Your goal is to answer the user's question by querying the MongoDB database.

CRITICAL MONGODB AGGREGATION RULE:
When you see aggregation results like [{{"_id": "Transportation", "total": 99000000000}}]:
- The "_id" field contains the grouped-by value (department name, supplier name, item name, etc.)
- Other fields contain the calculated values (totals, counts, averages)
- YOU MUST include BOTH the "_id" value AND the calculated values in your answer!

AVAILABLE TOOLS:
1. **get_collection_schema**: Inspect database structure
   - Use this if you don't know the exact field names
2. **translate_query**: Convert natural language to MongoDB query
   - Use this for questions about procurement data in the database
3. **execute_mongodb_query**: Run MongoDB queries
   - Use this to execute queries and get results
{web_search_section}

STRATEGY:
1. If the question is about procurement data, use get_collection_schema → translate_query → execute_mongodb_query
2. If the question is about external information (current events, definitions, etc.), use search_web
3. OBSERVE the raw results carefully:
   - Look at ALL fields including "_id"
   - For aggregation results, "_id" is usually the answer to "which/who" questions
   - For "Which department?" → look at "_id" field
   - For "Which supplier?" → look at "_id" field
   - For "What item?" → look at "_id" field
5. If results are empty or wrong, RETRY with a corrected query.
6. Formulate a complete answer with BOTH names and numbers.

EXAMPLES OF GOOD ANSWERS:
- "The department that spent the most is Transportation with $99 billion"
- "The top 5 suppliers are: 1. Acme Corp ($5M), 2. Tech Inc ($4M)..."
- "Q2 had the highest spending with $45 billion"

BAD ANSWERS (missing the "_id" value):
- "The total is $99 billion" ❌ (Where's the department name?)
- "The spending was $45 billion" ❌ (Which quarter?)

IMPORTANT: You are autonomous - use tools as needed, retry if wrong, and ALWAYS include the "_id" field values in your answer!"""

        # Initialize Conversation for this specific run
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_question)
        ]

        logger.info(f"🤖 Starting Agentic Loop for: {user_question}")

        final_response = ""
        iterations = 0
        max_iterations = 8  # Safety valve to prevent infinite loops
        tool_calls_made = []

        try:
            while iterations < max_iterations:
                iterations += 1
                logger.info(f"  🔄 Iteration {iterations}/{max_iterations}")

                # --- THINK ---
                # Invoke the LLM with the current conversation history
                ai_msg = self.llm_with_tools.invoke(messages)
                messages.append(ai_msg)  # Add agent's thought to history

                # Track token usage from response metadata
                if hasattr(ai_msg, 'response_metadata') and ai_msg.response_metadata:
                    metadata = ai_msg.response_metadata

                    # OpenAI format
                    if 'token_usage' in metadata:
                        usage = metadata['token_usage']
                        total_input_tokens += usage.get('prompt_tokens', 0)
                        total_output_tokens += usage.get('completion_tokens', 0)
                        logger.debug(f"  📊 Tokens this call: input={usage.get('prompt_tokens', 0)}, output={usage.get('completion_tokens', 0)}")

                    # Gemini format
                    elif 'usage_metadata' in metadata:
                        usage = metadata['usage_metadata']
                        total_input_tokens += usage.get('prompt_token_count', 0)
                        total_output_tokens += usage.get('candidates_token_count', 0)
                        logger.debug(f"  📊 Tokens this call: input={usage.get('prompt_token_count', 0)}, output={usage.get('candidates_token_count', 0)}")

                # Log what the agent is thinking
                if hasattr(ai_msg, 'content') and ai_msg.content:
                    logger.info(f"  💭 Agent thinking: {ai_msg.content[:100]}...")

                # --- DECIDE ---
                # If the LLM didn't call any tools, it means it has the final answer
                if not ai_msg.tool_calls:
                    final_response = ai_msg.content
                    logger.info(f"  ✅ Agent has final answer after {iterations} iterations")
                    break

                # --- ACT ---
                # Iterate through all tool calls requested by the LLM
                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]

                    logger.info(f"  🔧 Agent calling tool: {tool_name}")
                    tool_calls_made.append(tool_name)

                    # Execute the matching tool
                    tool_output = "Unknown Tool"

                    if tool_name == "get_collection_schema":
                        # Call the actual tool function
                        tool_output = self.tools[0].invoke({})

                    elif tool_name == "translate_query":
                        # Extract user_question from args
                        q = tool_args.get("user_question", "")
                        tool_output = self._tool_translate_query(q)

                    elif tool_name == "execute_mongodb_query":
                        # Extract query_json from args
                        q_json = tool_args.get("query_json", "")
                        tool_output = self._tool_execute_query(q_json)

                    elif tool_name == "search_web":
                        # Extract query and max_results from args
                        query = tool_args.get("query", "")
                        max_results = tool_args.get("max_results", 5)
                        tool_output = self._tool_search_web(query, max_results)

                    # --- OBSERVE ---
                    # Add the tool output back to the conversation as a ToolMessage
                    # This is the critical step where the Agent "sees" what happened
                    logger.info(f"  👀 Agent observing: {str(tool_output)[:150]}...")

                    messages.append(ToolMessage(
                        content=str(tool_output),
                        tool_call_id=tool_id
                    ))

            # End of Loop

            if iterations >= max_iterations:
                final_response = f"I apologize, but I reached the maximum number of reasoning steps ({max_iterations}) while trying to answer your question. The tools I used were: {', '.join(tool_calls_made)}. Please try rephrasing your question or making it more specific."
                logger.warning(f"  ⚠️  Agent hit max iterations")

            execution_time = (datetime.now() - start_time).total_seconds()

            # Extract clean text from response (handle list format from Gemini)
            clean_response = self._extract_text_from_response(final_response)

            # Update conversation history
            self._add_to_history(user_question, clean_response, None, [])

            return {
                "success": True,
                "user_question": user_question,
                "response": clean_response,
                "execution_time": execution_time,
                "iterations": iterations,
                "tools_used": tool_calls_made,
                "web_search_enabled": self.enable_web_search,
                "translated_query": None,  # Not tracked in agentic mode
                "results": [],  # Not tracked in agentic mode
                "results_count": 0,
                "error": None,
                "token_count": {
                    "input_token_count": total_input_tokens,
                    "output_token_count": total_output_tokens,
                    "total_token_count": total_input_tokens + total_output_tokens
                }
            }

        except Exception as e:
            logger.error(f"Error in agentic loop: {e}\n{traceback.format_exc()}")
            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": False,
                "user_question": user_question,
                "response": self._get_error_response(user_question, str(e)),
                "execution_time": execution_time,
                "iterations": iterations,
                "tools_used": tool_calls_made,
                "web_search_enabled": self.enable_web_search,
                "error": str(e),
                "translated_query": None,
                "results": [],
                "results_count": 0,
                "token_count": {
                    "input_token_count": total_input_tokens,
                    "output_token_count": total_output_tokens,
                    "total_token_count": total_input_tokens + total_output_tokens
                }
            }

    def _extract_text_from_response(self, response: Any) -> str:
        """
        Extract clean text from LLM response.
        Handles various response formats including list of dicts.
        """
        if isinstance(response, str):
            return response

        if isinstance(response, list):
            # Extract text from list of dict format: [{'type': 'text', 'text': '...'}]
            text_parts = []
            for item in response:
                if isinstance(item, dict) and 'text' in item:
                    text_parts.append(item['text'])
                elif isinstance(item, str):
                    text_parts.append(item)
            return ''.join(text_parts) if text_parts else str(response)

        # Fallback to string conversion
        return str(response)

    def _get_error_response(self, user_question: str, error: str) -> str:
        """Get user-friendly error response."""
        return (
            f"I encountered an error while processing your question: \"{user_question}\"\n\n"
            f"Error: {error}\n\n"
            "Please try rephrasing your question or make it more specific."
        )

    def _add_to_history(self, question: str, response: str, query: Dict, results: List[Dict]):
        """Add interaction to conversation history."""
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response,
            "query": query,
            "results_count": len(results) if results else 0
        })

        # Keep only last 10 interactions
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.conversation_history

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get agent statistics."""
        framework_name = "LangChain Agentic (ReAct Loop"
        if self.enable_web_search:
            framework_name += " + WebSearch)"
        else:
            framework_name += ")"

        return {
            "total_queries": len(self.conversation_history),
            "provider": self.llm_manager.provider,
            "model": self.llm_manager.model,
            "mongo_connected": self.mongo.is_connected(),
            "framework": framework_name,
            "web_search_enabled": self.enable_web_search
        }


def create_agentic_procurement_agent(
    mongo_client: MongoDBClient,
    llm_manager: LLMManager,
    use_few_shot: bool = True,
    enable_web_search: bool = True
) -> AgenticProcurementAgent:
    """
    Convenience function to create an Agentic procurement agent.

    Args:
        mongo_client: MongoDB client
        llm_manager: LLM manager
        use_few_shot: Use few-shot examples
        enable_web_search: Enable web search tool (default: True)

    Returns:
        AgenticProcurementAgent instance
    """
    return AgenticProcurementAgent(mongo_client, llm_manager, use_few_shot, enable_web_search)
