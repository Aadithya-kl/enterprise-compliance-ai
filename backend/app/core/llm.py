import os
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

def _get_gemini_client():
    try:
        from app.core.config import settings
        import os
        # Prioritize os environment to ensure reloads take effect
        api_key = os.environ.get("GEMINI_API_KEY", settings.GEMINI_API_KEY)
        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        return None

def check_llm_health() -> bool:
    """Verify connectivity to the LLM API."""
    gemini_client = _get_gemini_client()
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
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
def _execute_llm_call(
    gemini_client,
    model: str,
    contents: str,
    config: types.GenerateContentConfig
):
    logger.info(f"Making Gemini API call (model: {model})...")
    return gemini_client.models.generate_content(
        model=model,
        contents=contents,
        config=config
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
    gemini_client = _get_gemini_client()
    if not gemini_client:
        raise RuntimeError("Gemini client is not initialized. Ensure GEMINI_API_KEY is set.")

    try:
        config_kwargs = {"temperature": temperature}
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
            
        config = types.GenerateContentConfig(**config_kwargs)
        
        response = _execute_llm_call(
            gemini_client,
            settings.GEMINI_MODEL,
            prompt,
            config
        )
        return response.text
    except Exception as exc:
        exc_str = str(exc).lower()
        if "429" in exc_str or "quota" in exc_str or "exhausted" in exc_str or "503" in exc_str or "unavailable" in exc_str:
            from fastapi import HTTPException
            logger.error(f"Gemini API capacity issue: {exc}")
            raise HTTPException(
                status_code=429,
                detail="AI provider is currently experiencing high demand or quota limits. Please retry in a few moments."
            )
        logger.error(f"Gemini API request failed: {exc}", exc_info=True)
        raise RuntimeError(f"LLM call failed: {exc}") from exc
