import os
from dotenv import load_dotenv

def get_llm_config():
    """
    Loads the LLM configuration from environment variables.
    """
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file.")

    return {
        "model": "gpt-4.1-nano",
        "api_key": api_key,
        "temperature": 0.7,
    }