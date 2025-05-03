import uvicorn
from fastapi import FastAPI, HTTPException
from pathlib import Path
import logging # Import logging directly here as well

# Import components from our application modules
try:
    from .config import _log # Use the configured logger
    from .schemas import ProcessFolderRequest
    from .processing import process_folder_recursive
except ImportError as e:
    # Provide a clearer error message if imports fail
    logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    _log.error(f"Error importing application modules: {e}. Ensure you are running from the directory containing the 'app' folder or have installed it as a package.")
    # Define dummy components to allow script to load, but endpoints will fail
    class ProcessFolderRequest: pass
    async def process_folder_recursive(*args, **kwargs):
        raise RuntimeError("Application modules not loaded correctly.")

# Initialize FastAPI app
app = FastAPI(
    title="OCR Document Processing Service",
    description="Processes folders of documents (PDF, images, DOC/DOCX), extracts text, classifies content (bank statement vs. simple text) using Gemini, and saves structured JSON output.",
    version="1.0.0"
)

@app.post("/process-folder/", response_model=dict, tags=["Processing"])
async def process_folder_endpoint(request: ProcessFolderRequest):
    """
    API endpoint to trigger recursive folder processing.

    Takes an input folder path and an output folder path.
    Processes all supported documents within the input folder and saves
    structured JSON results to the output folder, preserving the directory structure.
    """
    _log.info(f"Received request to process folder: {request.input_folder}")
    try:
        input_folder = Path(request.input_folder)
        output_folder = Path(request.output_folder)

        # Basic validation on paths before starting async process
        if not input_folder.is_dir():
             _log.error(f"Input path is not a valid directory: {input_folder}")
             raise HTTPException(status_code=400, detail=f"Input folder does not exist or is not a directory: {input_folder}")

        # Start the processing
        await process_folder_recursive(str(input_folder), str(output_folder)) # Pass paths as strings if needed by underlying funcs

        success_message = f"OCR processing initiated successfully for folder: {input_folder}. Output will be saved to: {output_folder}"
        _log.info(success_message)
        # Note: Since processing is async and potentially long, consider returning immediately
        # and providing a way to check status later (e.g., background tasks, websockets).
        # For now, it waits for completion.
        return {"message": f"Processing complete for folder: {input_folder}. Output saved to: {output_folder}"}

    except ValueError as ve:
         # Catch specific ValueErrors raised for invalid input paths etc.
         _log.error(f"Value error during processing request: {ve}")
         raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as http_exc:
         # Re-raise HTTPExceptions directly
         raise http_exc
    except Exception as e:
        # Catch any other unexpected errors during processing
        _log.error(f"Unhandled error in /process-folder/ endpoint for input {request.input_folder}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal server error occurred during processing: {e}")


@app.get("/", tags=["Status"])
def read_root():
    """Health check endpoint."""
    _log.info("Root endpoint '/' accessed.")
    return {"message": "OCR Extraction Service (Modular App) is Running"}

# --- Main Execution ---
if __name__ == "__main__":
    _log.info("Starting OCR Extraction Service...")
    # Run FastAPI server using uvicorn
    # Use reload=True for development, False for production
    # Consider host and port configuration from environment variables
    uvicorn.run("app.main:app", host="0.0.0.0", port=8006, reload=True, log_level="info")
    # Note: If running with `python app/main.py`, uvicorn needs the app path like "main:app" relative to the execution context.
    # It's often better to run uvicorn directly from the command line: `uvicorn app.main:app --reload --port 8006` from the parent directory.
