from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ClaimStatus(str, Enum):
    green = "green"
    yellow = "yellow"
    red = "red"


class Citation(BaseModel):
    source: str
    snippet: Optional[str] = None
    url: Optional[str] = None


class Claim(BaseModel):
    statement: str
    status: ClaimStatus
    explanation: Optional[str] = None
    citations: List[Citation] = []


class AnalysisResponse(BaseModel):
    document_title: Optional[str] = None
    claims: List[Claim] = []
    analysis_markdown: Optional[str] = None

