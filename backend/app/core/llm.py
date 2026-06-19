import os
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize the Gemini client centrally
try:
    gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")
    gemini_client = None

def check_llm_health() -> bool:
    """Verify connectivity to the LLM API."""
    if not gemini_client:
        return False
    try:
        # Just retrieve the model info as a lightweight health check
        gemini_client.models.get(model=settings.GEMINI_MODEL)
        return True
    except Exception as exc:
        logger.error(f"LLM health check failed: {exc}")
        return False

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type(RuntimeError),
    reraise=True
)
def generate_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.0,
) -> str:
    """
    Generate a response using the Gemini API.
    
    Args:
        prompt: The user prompt.
        system_prompt: Optional system instructions.
        temperature: Controls randomness (0.0 = deterministic).
        
    Returns:
        The generated text response.
    """
    if not gemini_client:
        raise RuntimeError("Gemini client is not initialized. Ensure GEMINI_API_KEY is set.")

    try:
        config_kwargs = {"temperature": temperature}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
            
        response = gemini_client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs)
        )
        return response.text
    except Exception as exc:
        logger.error(f"Gemini API request failed: {exc}", exc_info=True)
        raise RuntimeError(f"LLM call failed: {exc}") from exc
