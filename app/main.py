import uvicorn
from fastapi import FastAPI, HTTPException
from pathlib import Path
import logging # Import logging directly here as well
import asyncio
import os
import shutil
import tempfile

#from watchdog.observers import Observer
#from watchdog.events import FileSystemEventHandler
from pydantic import BaseModel

# Import components from our application modules
try:
    from .config import _log, SUPPORTED_EXTENSIONS
    from .schemas import ProcessFolderRequest
    from .processing import process_folder_recursive, process_single_document, get_input_format
except ImportError as e:
    # Provide a clearer error message if imports fail
    logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    _log.error(f"Error importing application modules: {e}. Ensure you are running from the directory containing the 'app' folder or have installed it as a package.")
    # Define dummy components to allow script to load, but endpoints will fail
    class ProcessFolderRequest: pass
    async def process_folder_recursive(*args, **kwargs):
        raise RuntimeError("Application modules not loaded correctly.")

# Input schema for folder processing API endpoint
class ProcessFolderRequest(BaseModel):
    input_folder: str
    output_folder: str

# Initialize FastAPI app
app = FastAPI(
    title="OCR Document Processing Service",
    description="Processes folders of documents (PDF, images, DOC/DOCX), extracts text, classifies content (bank statement vs. simple text) using Gemini, and saves structured JSON output.",
    version="1.0.0"
)

#class NewFileHandler(FileSystemEventHandler):
#    def __init__(self, input_folder: str, output_folder: str):
#        self.input_folder = Path(input_folder)
#        self.output_folder = Path(output_folder)
#        super().__init__()

#    def on_created(self, event):
#        if not event.is_directory:
#            file_path = Path(event.src_path)
#            if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
#                _log.info(f"New file detected: {file_path.name}. Starting processing...")
#                # Use asyncio.create_task to run the processing in the background
#                asyncio.create_task(self.process_file(file_path))
#            else:
#                _log.info(f"Skipping unsupported file type: {file_path.name}")

#    async def process_file(self, file_path: Path):
#        """Processes a single file and deletes it afterwards."""
#        # Ensure the file is fully written before processing
#        await asyncio.sleep(1)  # Wait for 1 second
#        try:
#            # Use process_single_document directly
#            await process_single_document(
#                file_path.resolve(),  # Absolute path to the file
#                self.input_folder,  # Base input folder for relative paths
#                self.output_folder,  # Output folder
#                Path(tempfile.gettempdir()) # Use system temp dir
#            )
#            # No need to delete the file here, it's done in process_single_document

#        except Exception as e:
#            _log.error(f"Error processing {file_path}: {e}", exc_info=True)

@app.post("/process-folder/", tags=["Processing"], response_model=None)
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
         raise HTTPException(status_code=500, detail=f"An internal server error occurred during processing: {e}")


@app.get("/", tags=["Status"])
def read_root():
    """Health check endpoint."""
    _log.info("Root endpoint '/' accessed.")
    return {"message": "OCR Extraction Service (Modular App) is Running"}

#async def start_file_monitoring(input_folder: str, output_folder: str):
#    """Starts monitoring the input folder for new files."""
#    event_handler = NewFileHandler(input_folder, output_folder)
#    observer = Observer()
#    observer.schedule(event_handler, input_folder, recursive=False)
#    observer.start()
#    _log.info(f"File monitoring started on folder: {input_folder}")
#    try:
#        while True:
#            await asyncio.sleep(5)  # Check every 5 seconds
#        except KeyboardInterrupt:
#            observer.stop()
#        observer.join()
#    _log.info("File monitoring stopped.")

# --- Main Execution ---
if __name__ == "__main__":
    _log.info("Starting OCR Extraction Service...")
    # Define input and output folders (replace with your desired paths)
    #INPUT_FOLDER = "input_folder"
    #OUTPUT_FOLDER = "output_folder"

    # Create the input and output folders if they don't exist
    #os.makedirs(INPUT_FOLDER, exist_ok=True)
    #os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Start file monitoring in the background
    #asyncio.run(start_file_monitoring(INPUT_FOLDER, OUTPUT_FOLDER))

    # Run FastAPI server using uvicorn
    # Use reload=True for development, False for production
    # Consider host and port configuration from environment variables
    uvicorn.run("app.main:app", host="0.0.0.0", port=8006, log_level="info")
    # Note: If running with `python app/main.py`, uvicorn needs the app path like "main:app" relative to the execution context.
    # It's often better to run uvicorn directly from the command line: `uvicorn app.main:app --reload --port 8006` from the parent directory.
