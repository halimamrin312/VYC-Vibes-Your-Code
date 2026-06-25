"""
swarm/utils/llm.py
Decoupled, model-agnostic utility for executing LLM calls.
Supports Gemini, OpenAI, and Anthropic with dynamic imports and graceful fallbacks.
"""

import os
import logging
from typing import Optional, Any, Dict
from swarm.config import settings

import threading

logger = logging.getLogger("swarm.utils.llm")

# Global cache to preserve client connections across calls
_llm_clients: Dict[str, Any] = {}
_client_lock = threading.Lock()

def _get_client(provider: str, api_key: str) -> Any:
    """Retrieves or instantiates a cached client instance for the given provider."""
    cache_key = f"{provider}:{api_key}"
    with _client_lock:
        if cache_key not in _llm_clients:
            logger.info(f"Instantiating new client connection for provider: {provider}")
            if provider == "gemini":
                from google import genai
                _llm_clients[cache_key] = genai.Client(api_key=api_key)
            elif provider == "openai":
                import openai
                _llm_clients[cache_key] = openai.OpenAI(api_key=api_key)
            elif provider == "anthropic":
                import anthropic
                _llm_clients[cache_key] = anthropic.Anthropic(api_key=api_key)
        return _llm_clients[cache_key]

thread_local = threading.local()

def call_llm(system_prompt: str, prompt: str) -> Optional[str]:
    """
    Executes a text generation query to an LLM provider based on settings.
    If the provider SDK is missing or credentials are unconfigured, returns None.
    """
    provider = getattr(thread_local, "model_provider", None) or settings.model_provider
    provider = (provider or "").strip().lower()
    model = getattr(thread_local, "model_name", None) or settings.model_name
    model = (model or "").strip()

    logger.info(f"Initiating LLM call (Provider: {provider}, Model: {model})")

    if provider == "gemini":
        api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            logger.warning("Gemini API key is unconfigured.")
            return None
        
        try:
            from google.genai import types
            client = _get_client("gemini", api_key)
            response = client.models.generate_content(
                model=model or "gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}", exc_info=True)
            return None

    elif provider == "openai":
        api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            logger.warning("OpenAI API key is unconfigured.")
            return None

        try:
            client = _get_client("openai", api_key)
            response = client.chat.completions.create(
                model=model or "gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            return response.choices[0].message.content
        except ImportError:
            logger.error("openai package not installed.")
            return None
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}", exc_info=True)
            return None

    elif provider == "anthropic":
        api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key or api_key == "your_anthropic_api_key_here":
            logger.warning("Anthropic API key is unconfigured.")
            return None

        try:
            client = _get_client("anthropic", api_key)
            response = client.messages.create(
                model=model or "claude-3-5-sonnet-20241022",
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            return response.content[0].text
        except ImportError:
            logger.error("anthropic package not installed.")
            return None
        except Exception as e:
            logger.error(f"Anthropic API call failed: {str(e)}", exc_info=True)
            return None

    else:
        logger.warning(f"Unsupported LLM provider: {provider}")
        return None
