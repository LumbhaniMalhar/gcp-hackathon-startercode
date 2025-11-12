import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import pdf_utils, vertex
from .config import settings
from .schemas import AnalysisResponse

logger = logging.getLogger("agentic-claims-verifier")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agentic Claims Verifier API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15MB


@app.get("/health", response_model=dict[str, str])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_document(file: UploadFile = File(...)) -> AnalysisResponse:
    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds 15MB limit.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(contents)
        temp_path = Path(temp_file.name)

    try:
        text = pdf_utils.extract_text_from_pdf(temp_path)
        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail="Unable to extract text from PDF. Ensure the document is not scanned-only.",
            )
        chunks = list(
            pdf_utils.chunk_text(
                text,
                chunk_size=settings.max_pdf_chunk_size,
                overlap=settings.pdf_chunk_overlap,
            )
        )
        logger.info("Extracted %d text chunks from PDF", len(chunks))
        # print(chunks[0])
        response = await vertex.extract_and_verify_claims(chunks)
        return response
    finally:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.warning("Failed to remove temporary file %s: %s", temp_path, exc)

