"""
LLM Manager V2 - Enhanced with LangChain ChatOpenAI support
Unified interface for both Gemini and OpenAI using LangChain chat models.
"""
import logging
import json
from typing import Optional, Dict, Any
import os

import config

logger = logging.getLogger(__name__)


class LLMManagerV2:
    """
    Enhanced LLM Manager using LangChain chat models for both providers.
    Provides unified interface for Gemini and OpenAI.
    """

    def __init__(
        self,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        use_adc: bool = False,
        model: Optional[str] = None,
        vertex_project: Optional[str] = None,
        vertex_location: Optional[str] = None,
        organization: Optional[str] = None
    ):
        """
        Initialize LLM Manager V2.

        Args:
            provider: "gemini" or "openai"
            api_key: API key for the provider
            use_adc: Use Application Default Credentials for Gemini (Vertex AI)
            model: Model name (defaults to config values)
            vertex_project: Vertex AI project (for Gemini ADC)
            vertex_location: Vertex AI location (for Gemini ADC)
            organization: OpenAI organization ID (optional)
        """
        self.provider = provider.lower()
        if self.provider == "gpt":
            self.provider = "openai"  # Normalize to "openai"

        self.api_key = api_key
        self.use_adc = use_adc
        self.vertex_project = vertex_project or config.VERTEX_PROJECT
        self.vertex_location = vertex_location or config.VERTEX_LOCATION
        self.organization = organization

        # Set model based on provider
        if model:
            self.model = model
        else:
            if self.provider == "gemini":
                self.model = config.GEMINI_MODEL
            elif self.provider == "openai":
                self.model = config.OPENAI_MODEL
            else:
                raise ValueError(f"Unsupported provider: {provider}")

        # Initialize the LangChain chat model
        self.chat_model = None
        self._init_chat_model()

    def _init_chat_model(self):
        """Initialize the appropriate LangChain chat model based on provider."""
        if self.provider == "gemini":
            self._init_gemini_chat()
        elif self.provider == "openai":
            self._init_openai_chat()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _init_gemini_chat(self):
        """Initialize Gemini using LangChain ChatGoogleGenerativeAI."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from google.oauth2 import service_account

            # Priority 1: Try API key mode
            api_key = self.api_key or config.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_CLOUD_API_KEY")

            if api_key:
                logger.info("Initializing Gemini with API key mode (LangChain ChatGoogleGenerativeAI)")

                # Check if this is Vertex AI Express Mode key (AQ. prefix)
                if api_key.startswith("AQ."):
                    logger.info("Detected Vertex AI Express Mode API key")
                    self.chat_model = ChatGoogleGenerativeAI(
                        model=self.model,
                        temperature=config.DEFAULT_TEMPERATURE,
                        max_output_tokens=config.DEFAULT_MAX_TOKENS,  # Changed from max_tokens
                        google_api_key=api_key,
                        vertexai=True,  # Required for Vertex AI Express Mode
                        convert_system_message_to_human=True
                    )
                else:
                    logger.info("Detected standard Gemini Developer API key")
                    self.chat_model = ChatGoogleGenerativeAI(
                        model=self.model,
                        temperature=config.DEFAULT_TEMPERATURE,
                        max_output_tokens=config.DEFAULT_MAX_TOKENS,  # Changed from max_tokens
                        google_api_key=api_key,
                        convert_system_message_to_human=True
                    )

                logger.info(f"✓ Gemini chat model initialized: {self.model}")
                return

            # Priority 2: Fallback to Service Account
            sa_key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if self.use_adc or sa_key_path:
                logger.info(f"Initializing Gemini with Service Account - Project: {self.vertex_project}")

                credentials = service_account.Credentials.from_service_account_file(
                    sa_key_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )

                self.chat_model = ChatGoogleGenerativeAI(
                    model=self.model,
                    temperature=config.DEFAULT_TEMPERATURE,
                    max_output_tokens=config.DEFAULT_MAX_TOKENS,  # Changed from max_tokens
                    credentials=credentials,
                    project=self.vertex_project,
                    location=self.vertex_location,
                    vertexai=True,
                    convert_system_message_to_human=True
                )

                logger.info(f"✓ Gemini chat model initialized with service account: {self.model}")
                return

            # No authentication found
            raise ValueError(
                "Gemini authentication required. "
                "Please provide API key (GOOGLE_API_KEY) or configure service account (GOOGLE_APPLICATION_CREDENTIALS)."
            )

        except Exception as e:
            logger.error(f"Failed to initialize Gemini chat model: {e}")
            raise

    def _init_openai_chat(self):
        """Initialize OpenAI using LangChain ChatOpenAI."""
        try:
            from langchain_openai import ChatOpenAI

            logger.info("Initializing OpenAI with LangChain ChatOpenAI")

            api_key = self.api_key or config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key required. "
                    "Please provide via api_key parameter or OPENAI_API_KEY environment variable."
                )

            # Initialize ChatOpenAI with proper parameters
            # GPT-5 only supports temperature=1 (default)
            if self.model == "gpt-5":
                logger.info("GPT-5 detected - using default temperature (1)")
                self.chat_model = ChatOpenAI(
                    model=self.model,
                    # temperature not set - uses default of 1
                    max_tokens=config.DEFAULT_MAX_TOKENS,
                    api_key=api_key,
                    max_retries=2,
                    timeout=60,
                    organization=self.organization
                )
            else:
                self.chat_model = ChatOpenAI(
                    model=self.model,
                    temperature=config.DEFAULT_TEMPERATURE,
                    max_tokens=config.DEFAULT_MAX_TOKENS,
                    api_key=api_key,
                    max_retries=2,
                    timeout=60,
                    organization=self.organization
                )

            logger.info(f"✓ OpenAI chat model initialized: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI chat model: {e}")
            raise

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text response from LLM using LangChain chat model.

        Args:
            prompt: User prompt
            temperature: Sampling temperature (overrides default)
            max_tokens: Maximum tokens to generate (overrides default)
            system_prompt: Optional system prompt

        Returns:
            Generated text response
        """
        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            # Build messages
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))

            # Create a new model instance if temperature/max_tokens are overridden
            if temperature is not None or max_tokens is not None:
                # Use correct parameter name based on provider
                if self.provider == "gemini":
                    model = self.chat_model.bind(
                        temperature=temperature if temperature is not None else config.DEFAULT_TEMPERATURE,
                        max_output_tokens=max_tokens if max_tokens is not None else config.DEFAULT_MAX_TOKENS
                    )
                elif self.provider == "openai" and self.model == "gpt-5":
                    # GPT-5 only supports default temperature
                    model = self.chat_model.bind(
                        max_tokens=max_tokens if max_tokens is not None else config.DEFAULT_MAX_TOKENS
                    )
                else:
                    model = self.chat_model.bind(
                        temperature=temperature if temperature is not None else config.DEFAULT_TEMPERATURE,
                        max_tokens=max_tokens if max_tokens is not None else config.DEFAULT_MAX_TOKENS
                    )
            else:
                model = self.chat_model

            # Invoke the chat model
            response = model.invoke(messages)

            # Extract text from response
            if hasattr(response, 'content'):
                content = response.content
                # Handle list format (Gemini sometimes returns this)
                if isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict) and 'text' in item:
                            text_parts.append(item['text'])
                        elif isinstance(item, str):
                            text_parts.append(item)
                    return ''.join(text_parts)
                return str(content)

            return str(response)

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def generate_json(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response from LLM.

        Args:
            prompt: User prompt
            temperature: Sampling temperature
            system_prompt: Optional system prompt

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If response is not valid JSON
        """
        try:
            # Add instruction to return JSON
            json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON, no additional text."

            if self.provider == "openai":
                # OpenAI supports JSON mode natively
                from langchain_core.messages import SystemMessage, HumanMessage

                messages = []
                if system_prompt:
                    messages.append(SystemMessage(content=system_prompt))
                messages.append(HumanMessage(content=json_prompt))

                # Use with_structured_output or bind for JSON mode
                model = self.chat_model.bind(response_format={"type": "json_object"})
                # GPT-5 only supports default temperature
                if temperature is not None and self.model != "gpt-5":
                    model = model.bind(temperature=temperature)

                response = model.invoke(messages)
                response_text = response.content
            else:
                # For Gemini, request JSON in prompt
                response_text = self.generate(
                    json_prompt,
                    temperature=temperature or config.QUERY_GENERATION_TEMPERATURE,
                    system_prompt=system_prompt
                )

            # Parse JSON
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}\nResponse: {response_text}")
            raise ValueError(f"LLM did not return valid JSON: {e}")
        except Exception as e:
            logger.error(f"Error generating JSON response: {e}")
            raise

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the LLM connection with a simple prompt.

        Returns:
            Dict with test results
        """
        try:
            logger.info(f"Testing {self.provider} connection...")

            response = self.generate(
                "Respond with 'OK' if you can read this message.",
                temperature=0.1,
                max_tokens=50
            )

            logger.info(f"✓ {self.provider} connection successful")

            return {
                "success": True,
                "provider": self.provider,
                "model": self.model,
                "response": response
            }

        except Exception as e:
            logger.error(f"✗ {self.provider} connection failed: {e}")
            return {
                "success": False,
                "provider": self.provider,
                "model": self.model,
                "error": str(e)
            }


def create_llm_manager_v2(
    provider: str = "gemini",
    api_key: Optional[str] = None,
    use_adc: bool = False,
    **kwargs
) -> LLMManagerV2:
    """
    Convenience function to create an LLM manager V2.

    Args:
        provider: "gemini" or "openai" (also accepts "gpt")
        api_key: API key
        use_adc: Use Application Default Credentials for Gemini
        **kwargs: Additional arguments for LLMManagerV2

    Returns:
        LLMManagerV2 instance
    """
    return LLMManagerV2(provider=provider, api_key=api_key, use_adc=use_adc, **kwargs)


# Backwards compatibility alias
def create_llm_manager(
    provider: str = "gemini",
    api_key: Optional[str] = None,
    use_adc: bool = False,
    **kwargs
) -> LLMManagerV2:
    """
    Backwards compatible alias for create_llm_manager_v2.

    Args:
        provider: "gemini" or "openai" (also accepts "gpt")
        api_key: API key
        use_adc: Use Application Default Credentials for Gemini
        **kwargs: Additional arguments

    Returns:
        LLMManagerV2 instance
    """
    return create_llm_manager_v2(provider=provider, api_key=api_key, use_adc=use_adc, **kwargs)


# Backwards compatibility alias
LLMManager = LLMManagerV2
