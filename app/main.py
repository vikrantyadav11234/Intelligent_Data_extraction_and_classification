import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import logging
import asyncio
import os
import tempfile
from contextlib import asynccontextmanager
import time

# Imports from your app modules (adjust relative paths if necessary)
try:
    from .config import _log, SUPPORTED_EXTENSIONS
    from .schemas import ProcessFolderRequest
    from .processing import process_folder_recursive, process_single_document
except ImportError as e:
    logging.basicConfig(level=logging.INFO)
    _log = logging.getLogger(__name__)
    _log.error(f"Error importing modules: {e}")

    SUPPORTED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}

    class ProcessFolderRequest(BaseModel):
        input_folder: str
        output_folder: str

    async def process_folder_recursive(*args, **kwargs):
        raise RuntimeError("process_folder_recursive not implemented.")

    async def process_single_document(*args, **kwargs):
        raise RuntimeError("process_single_document not implemented.")

# Initialize FastAPI app with lifespan
INPUT_FOLDER = os.path.abspath("D:\Models\ocr_extraction\Intelligent_Data_extraction_and_classification\input_folder")
OUTPUT_FOLDER = os.path.abspath("D:\Models\ocr_extraction\Intelligent_Data_extraction_and_classification\output_folder")
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Async queue to manage file processing order
file_queue = asyncio.Queue()

# Track files already in processing or processed
processing_files = set()
processing_lock = asyncio.Lock()

# Wait until file is fully written and ready for access
async def wait_for_file_ready(file_path: Path, timeout=10):
    start_time = time.time()
    last_size = -1

    while True:
        if not file_path.exists():
            await asyncio.sleep(0.2)
        else:
            current_size = file_path.stat().st_size
            if current_size == last_size:
                return True
            last_size = current_size
            await asyncio.sleep(0.5)
        if time.time() - start_time > timeout:
            _log.error(f"File {file_path} not ready after {timeout}s.")
            return False

# Async processor for a single file
async def process_file(file_path: Path):
    _log.info(f"Started processing: {file_path}")
    await asyncio.sleep(2)  # Simulate processing time if needed
    if not file_path.exists():
        _log.error(f"File not found during processing: {file_path}")
        return
    await process_single_document(
        file_path.resolve(),
        INPUT_FOLDER,
        OUTPUT_FOLDER,
        Path(tempfile.gettempdir())
    )
    _log.info(f"Finished processing: {file_path}")

# Async worker to process files in the queue
async def file_processor_worker():
    while True:
        file_path = await file_queue.get()
        try:
            async with processing_lock:
                if str(file_path) in processing_files:
                    _log.info(f"File already in progress: {file_path}")
                    continue
                processing_files.add(str(file_path))

            await process_file(file_path)

        except Exception as e:
            _log.error(f"Error processing {file_path}: {e}", exc_info=True)
        finally:
            async with processing_lock:
                processing_files.discard(str(file_path))
            file_queue.task_done()

# Watch for new files or scan existing files on startup
async def file_watcher():
    _log.info(f"Watching folder: {INPUT_FOLDER}")
    known_files = set()

    while True:
        await asyncio.sleep(3)
        files = [f for f in os.listdir(INPUT_FOLDER) if os.path.isfile(os.path.join(INPUT_FOLDER, f))]

        for file_name in files:
            file_path = Path(os.path.join(INPUT_FOLDER, file_name))

            if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                async with processing_lock:
                    if str(file_path) not in processing_files and file_path not in known_files:
                        if await wait_for_file_ready(file_path):
                            _log.info(f"New or existing file detected: {file_path}. Adding to queue.")
                            await file_queue.put(file_path)
                            known_files.add(file_path)

# Start file monitoring and processing tasks
async def start_file_monitoring(input_folder: str, output_folder: str):
    # Start processing worker
    asyncio.create_task(file_processor_worker())
    # Start file watcher
    asyncio.create_task(file_watcher())

@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_file_monitoring(INPUT_FOLDER, OUTPUT_FOLDER)
    yield
    _log.info("Stopping file monitoring...")

# FastAPI app setup
app = FastAPI(
    title="OCR Document Processing Service",
    description="Processes folders of documents (PDF, images) with OCR, extracts text, classifies content, and saves structured JSON output.",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/process-folder/", tags=["Processing"])
async def process_folder_endpoint(request: ProcessFolderRequest):
    _log.info(f"Received request to process folder: {request.input_folder}")
    try:
        input_folder = Path(request.input_folder)
        output_folder = Path(request.output_folder)

        if not input_folder.is_dir():
            _log.error(f"Invalid input directory: {input_folder}")
            raise HTTPException(status_code=400, detail=f"Input folder does not exist or is not a directory: {input_folder}")

        await process_folder_recursive(str(input_folder), str(output_folder))

        success_msg = f"OCR processing initiated for: {input_folder}, output at: {output_folder}"
        _log.info(success_msg)
        return {"message": success_msg}

    except ValueError as ve:
        _log.error(f"Value error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        _log.error(f"Internal error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@app.get("/", tags=["Status"])
def read_root():
    _log.info("Root endpoint accessed.")
    return {"message": "OCR Extraction Service is Running"}

# Run via: uvicorn app.main:app --reload --port 8006
if __name__ == "__main__":
    _log.info("Starting OCR Extraction Service...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8006, log_level="info")
