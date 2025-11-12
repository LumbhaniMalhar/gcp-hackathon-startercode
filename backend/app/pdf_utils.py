from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


def extract_text_from_pdf(path: Path) -> str:
    reader = PdfReader(path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> Iterable[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap.")
    start = 0
    end = chunk_size
    length = len(text)
    while start < length:
        yield text[start:end]
        start = end - overlap
        end = start + chunk_size

