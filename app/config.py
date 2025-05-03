import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_log = logging.getLogger(__name__) # Use __name__ for logger hierarchy

# --- Gemini API Setup ---
GENAI_API_KEY = os.getenv("GENAI_API_KEY")
if not GENAI_API_KEY:
    _log.warning("GENAI_API_KEY not found in environment variables. Using default or potentially failing.")
    GENAI_API_KEY = "default_api_key" # Provide a default or handle error

try:
    genai.configure(api_key=GENAI_API_KEY)
    _log.info("Gemini API configured successfully.")
except Exception as e:
    _log.error(f"Failed to configure Gemini API: {e}")
    # Decide how to handle this - raise error, exit, or continue with limited functionality?
    # For now, we'll log the error and potentially let it fail later if Gemini is used.

# --- Other Configurations ---
# Example: Define supported file types centrally
SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.pdf', '.doc', '.docx']
MAX_GEMINI_INPUT_LENGTH = 30000 # Character limit for Gemini input
