"""
Query translator module using LangChain for converting natural language to MongoDB queries.
Uses FewShotPromptTemplate and LLMChain for structured query generation.
"""
import logging
import json
from typing import Dict, Any, Optional

import os
# Updated imports for LangChain 1.2.9+
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
# LLMChain deprecated in 1.2.9+, use direct LLM invocation instead
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from google.oauth2 import service_account

from prompts.few_shot_examples import FEW_SHOT_EXAMPLES
import config

logger = logging.getLogger(__name__)


class LangChainQueryTranslator:
    """
    Translates natural language queries into MongoDB queries using LangChain.
    Implements few-shot prompting with FewShotPromptTemplate.
    """

    def __init__(self, llm_manager, num_examples: int = 5):
        """
        Initialize LangChain query translator.

        Args:
            llm_manager: LLM manager instance (for compatibility)
            num_examples: Number of few-shot examples to use
        """
        self.llm_manager = llm_manager
        self.num_examples = num_examples

        # Create LangChain LLM based on provider
        self.llm = self._create_langchain_llm()

        # Create few-shot prompt template
        self.prompt_template = self._create_few_shot_template()

    def _create_langchain_llm(self):
        """Create LangChain LLM instance based on provider."""
        provider = self.llm_manager.provider

        # Normalize provider name for backwards compatibility
        if provider == "openai":
            provider = "gpt"

        if provider == "gemini":
            # Default: Use API key mode
            api_key = self.llm_manager.api_key or config.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY")

            if api_key:
                # Check if this is a Vertex AI Express Mode key (starts with AQ.)
                # or standard Developer API key (starts with AIzaSy)
                if api_key.startswith("AQ."):
                    logger.info("Using Vertex AI Express Mode with API key - LangChain")
                    # CRITICAL: For Vertex AI Express Mode, use vertexai=True but NO project/location
                    # See: https://github.com/langchain-ai/langchain-google/issues/1473
                    return ChatGoogleGenerativeAI(
                        model=self.llm_manager.model,
                        temperature=config.QUERY_GENERATION_TEMPERATURE,
                        max_tokens=config.DEFAULT_MAX_TOKENS,
                        google_api_key=api_key,
                        vertexai=True,  # Required for Vertex AI Express Mode
                        # DO NOT include project or location - causes OAuth2 fallback
                        convert_system_message_to_human=True
                    )
                else:
                    logger.info("Using Gemini Developer API with API key - LangChain")
                    # Standard Developer API (AIzaSy keys)
                    return ChatGoogleGenerativeAI(
                        model=self.llm_manager.model,
                        temperature=config.QUERY_GENERATION_TEMPERATURE,
                        max_tokens=config.DEFAULT_MAX_TOKENS,
                        google_api_key=api_key,
                        convert_system_message_to_human=True
                    )

            # Fallback: Check if using Service Account
            sa_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if sa_key_path:
                logger.info(f"Using Vertex AI with Service Account: {sa_key_path}")

                # Load service account credentials
                credentials = service_account.Credentials.from_service_account_file(
                    sa_key_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )

                # Use ChatGoogleGenerativeAI with Vertex AI backend
                return ChatGoogleGenerativeAI(
                    model=self.llm_manager.model,
                    temperature=config.QUERY_GENERATION_TEMPERATURE,
                    max_tokens=config.DEFAULT_MAX_TOKENS,
                    credentials=credentials,
                    project=self.llm_manager.vertex_project,
                    location=self.llm_manager.vertex_location,
                    vertexai=True,
                    convert_system_message_to_human=True
                )

            # No authentication found
            raise ValueError(
                "Gemini authentication required. "
                "Please provide API key (GOOGLE_API_KEY) or configure service account (GOOGLE_APPLICATION_CREDENTIALS)."
            )

        elif provider == "gpt":
            return ChatOpenAI(
                model=self.llm_manager.model,
                temperature=config.QUERY_GENERATION_TEMPERATURE,
                max_tokens=config.DEFAULT_MAX_TOKENS,
                api_key=self.llm_manager.api_key
            )

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _create_few_shot_template(self) -> FewShotPromptTemplate:
        """
        Create few-shot prompt template with examples.

        Returns:
            FewShotPromptTemplate configured with procurement query examples
        """
        import json

        # Format examples for few-shot template
        # CRITICAL: Convert query dict to JSON string and escape braces for format()
        formatted_examples = []
        for ex in FEW_SHOT_EXAMPLES[:self.num_examples]:
            # Double the braces to escape them for Python's format()
            query_json = json.dumps(ex["query"], indent=2)
            query_escaped = query_json.replace("{", "{{").replace("}", "}}")

            formatted_examples.append({
                "user_query": ex["user_query"],
                "query_type": ex["query_type"],
                "query": query_escaped,  # Escaped JSON string
                "explanation": ex["explanation"]
            })

        # Example formatter template
        example_template = """
User Query: {user_query}
MongoDB Query Type: {query_type}
MongoDB Query: {query}
Explanation: {explanation}
"""

        example_prompt = PromptTemplate(
            input_variables=["user_query", "query_type", "query", "explanation"],
            template=example_template
        )

        examples = formatted_examples

        # System prompt prefix
        prefix = """You are an expert MongoDB query generator for a California state procurement database.

DATABASE SCHEMA:
- creation_date (string, MM/DD/YYYY), creation_date_parsed (datetime), creation_year, creation_month, creation_quarter (integers)
- fiscal_year (string: "2013-2014"), fiscal_quarter (string: "Q1", "Q2", "Q3", "Q4")
  * Fiscal year runs July-June: Q1=Jul-Sep, Q2=Oct-Dec, Q3=Jan-Mar, Q4=Apr-Jun
- purchase_date, lpa_number, purchase_order_number, requisition_number
- acquisition_type, acquisition_method (e.g., "IT Goods", "WSCA/Coop")
- department_name, supplier_name, supplier_code
- item_name, item_description, quantity
- unit_price, total_price (numbers in dollars)
- commodity_title, class_code, family_code, segment_code, location

INSTRUCTIONS:
1. Analyze the user's natural language question
2. Generate a valid MongoDB query or aggregation pipeline
3. Return ONLY valid JSON with this structure:
{{
  "query_type": "find" | "aggregate",
  "query": {{...}},
  "explanation": "Brief explanation"
}}

EXAMPLES:
"""

        # Suffix with the actual user query
        suffix = """
Now translate this query:
User Query: {user_query}

Return ONLY the JSON object, no additional text:"""

        # Create few-shot template
        few_shot_prompt = FewShotPromptTemplate(
            examples=examples,
            example_prompt=example_prompt,
            prefix=prefix,
            suffix=suffix,
            input_variables=["user_query"],
            example_separator="\n---\n"
        )

        return few_shot_prompt

    def translate(self, user_query: str) -> Dict[str, Any]:
        """
        Translate natural language query to MongoDB query using LangChain.

        Args:
            user_query: User's natural language question

        Returns:
            Dict with query_type, query, and explanation

        Raises:
            ValueError: If translation fails
        """
        try:
            logger.info(f"Translating query with LangChain: {user_query}")

            # Format the prompt
            formatted_prompt = self.prompt_template.format(user_query=user_query)

            # Invoke LLM directly (LLMChain deprecated in 1.2.9+)
            llm_response = self.llm.invoke(formatted_prompt)

            logger.info(f"LLM response type: {type(llm_response)}")
            logger.info(f"LLM response dir: {[x for x in dir(llm_response) if not x.startswith('_')][:20]}")

            # Extract content from response
            result = None
            if isinstance(llm_response, list):
                logger.info(f"Response is list with {len(llm_response)} items")
                if llm_response and hasattr(llm_response[0], 'content'):
                    result = llm_response[0].content
                elif llm_response:
                    result = str(llm_response[0])
                else:
                    result = ""
            elif hasattr(llm_response, 'content'):
                logger.info("Response has content attribute")
                content = llm_response.content
                # Content itself might be a list
                if isinstance(content, list):
                    logger.info(f"Content is list: {content}")
                    # Extract text from content list
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                        elif isinstance(item, str):
                            text_parts.append(item)
                        else:
                            text_parts.append(str(item))
                    result = ''.join(text_parts)
                else:
                    result = content
            else:
                logger.info("Using str() fallback")
                result = str(llm_response)

            logger.info(f"Extracted result type: {type(result)}, length: {len(result) if isinstance(result, str) else 'N/A'}")

            # Ensure result is a string
            if not isinstance(result, str):
                result = str(result)

            # Parse JSON response
            result = result.strip()

            # Remove markdown code blocks if present
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()

            # Parse JSON
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}\nRaw LLM response: {result[:500]}")
                raise ValueError(f"LLM did not return valid JSON: {e}")

            # Log what we got from LLM
            logger.info(f"LLM returned: {json.dumps(parsed, indent=2)[:500]}")

            # Validate response format
            if not self._validate_response_format(parsed):
                logger.error(f"Response format validation failed. Got: {parsed}")
                raise ValueError(f"Invalid response format: {parsed}")

            # Validate query structure
            query_type = parsed["query_type"]
            query = parsed["query"]

            logger.info(f"Validating query_type={query_type}, query keys: {list(query.keys()) if isinstance(query, dict) else 'not a dict'}")

            if not self.validate_query(query_type, query):
                logger.error(f"Query validation failed for query_type={query_type}, query={query}")
                raise ValueError(f"Generated query failed validation: {query}")

            logger.info(f"✓ Query translated successfully with LangChain: {query_type}")

            return {
                "query_type": query_type,
                "query": query,
                "explanation": parsed.get("explanation", "")
            }

        except KeyError as e:
            logger.error(f"KeyError accessing field: {e}\nParsed response: {parsed if 'parsed' in locals() else 'N/A'}")
            raise ValueError(f"LLM response missing required field: {e}")
        except Exception as e:
            logger.error(f"Error translating query with LangChain: {e}\nFull traceback:", exc_info=True)
            raise

    def _validate_response_format(self, response: Dict[str, Any]) -> bool:
        """Validate that LLM response has correct format."""
        required_fields = ["query_type", "query"]

        if not all(field in response for field in required_fields):
            logger.error(f"Missing required fields in response: {response}")
            return False

        if response["query_type"] not in ["find", "aggregate"]:
            logger.error(f"Invalid query_type: {response['query_type']}")
            return False

        return True

    def validate_query(self, query_type: str, query: Dict[str, Any]) -> bool:
        """Validate MongoDB query structure."""
        try:
            # First check if query is actually a dict
            if not isinstance(query, dict):
                logger.error(f"Query must be a dict, got {type(query)}: {query}")
                return False

            if query_type == "find":
                if "filter" not in query:
                    logger.error(f"Find query missing 'filter' field. Got keys: {list(query.keys())}")
                    return False

                if not isinstance(query["filter"], dict):
                    logger.error(f"Filter must be a dict, got {type(query['filter'])}")
                    return False

                # Ensure there's a limit
                if "limit" not in query:
                    query["limit"] = config.MAX_QUERY_RESULTS
                    logger.info(f"Added default limit: {config.MAX_QUERY_RESULTS}")

            elif query_type == "aggregate":
                if "pipeline" not in query:
                    logger.error(f"Aggregate query missing 'pipeline' field. Got keys: {list(query.keys())}, query: {query}")
                    return False

                pipeline = query["pipeline"]
                if not isinstance(pipeline, list):
                    logger.error(f"Pipeline must be a list, got {type(pipeline)}")
                    return False

                if len(pipeline) == 0:
                    logger.error("Pipeline cannot be empty")
                    return False

                # Check for destructive operations
                destructive_stages = ["$out", "$merge"]
                for i, stage in enumerate(pipeline):
                    if not isinstance(stage, dict):
                        logger.error(f"Invalid pipeline stage at index {i}: {stage} (type: {type(stage)})")
                        return False
                    for stage_name in stage.keys():
                        if stage_name in destructive_stages:
                            logger.error(f"Query contains destructive operation: {stage_name}")
                            return False

            else:
                logger.error(f"Unknown query_type: {query_type}")
                return False

            return True

        except KeyError as e:
            logger.error(f"KeyError validating query: {e}, query={query}")
            return False
        except Exception as e:
            logger.error(f"Error validating query: {e}", exc_info=True)
            return False


def create_langchain_query_translator(llm_manager, num_examples: int = 5):
    """
    Convenience function to create a LangChain query translator.

    Args:
        llm_manager: LLM manager instance
        num_examples: Number of few-shot examples to use

    Returns:
        LangChainQueryTranslator instance
    """
    return LangChainQueryTranslator(llm_manager, num_examples)
