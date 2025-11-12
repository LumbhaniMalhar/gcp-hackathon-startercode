from __future__ import annotations
import logging
import asyncio
from collections.abc import Sequence
from typing import Any

import httpx
from google.auth import default
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .schemas import AnalysisResponse, Claim, ClaimStatus

_logger = logging.getLogger(__name__)

_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)
_cached_credentials: Credentials | None = None
_VERIFICATION_CONCURRENCY = 5


def _get_credentials() -> Credentials:
    global _cached_credentials
    if _cached_credentials is None:
        creds, _ = default(scopes=_SCOPES)
        _cached_credentials = creds
    if not _cached_credentials.valid:
        _cached_credentials.refresh(Request())
    return _cached_credentials


def _format_document_chunks(chunks: Sequence[str]) -> str:
    return "\n\n---\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())


def _build_claim_extraction_prompt(document_text: str) -> str:
    instructions = """You are an expert analyst summarizing checkable claims in a document.
Read the document text and respond in Markdown using the following format:
Title: <optional document title or leave blank>
Claims:
- <claim 1>
- <claim 2>
Ensure each claim is concise and on a separate bullet starting with '- '.
Do not add any other commentary or sections."""
    return f"{instructions}\n\nDocument text:\n{document_text}"


def _build_claim_verification_prompt(
    claim_statement: str, document_text: str, document_title: str | None
) -> str:
    title_block = f"Document title: {document_title}\n" if document_title else ""
    instructions = """You are a specialized fact-checking agent verifying a single claim.
Provide your findings in Markdown using this exact template:
Status: <green|yellow|red>
Explanation: <short rationale>
Citations:
- <source or domain> — <brief snippet> (<url>)
If no citations are available, write 'Citations: none'.
Keep the response focused and do not add extra sections."""
    return (
        f"{instructions}\n\n"
        f"Claim to verify:\n{claim_statement}\n\n"
        f"{title_block}"
        f"Document context:\n{document_text}"
    )


def _build_request_payload(
    prompt: str, response_schema: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": _build_generation_config(response_schema),
        "tools": [
            {
                "googleSearch": {},
            }
        ],
    }


def _build_generation_config(response_schema: dict[str, Any] | None) -> dict[str, Any]:
    config: dict[str, Any] = {
        "temperature": 0.2,
        "topP": 0.8,
        "topK": 40,
        "maxOutputTokens": 2048,
    }
    if response_schema:
        config["responseSchema"] = response_schema
        config["responseMimeType"] = "application/json"
    return config


async def _post_to_vertex(payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.gcp_project_id:
        raise RuntimeError("GCP_PROJECT_ID is not configured.")
    credentials = _get_credentials()
    endpoint = (
        f"https://{settings.gcp_location}-aiplatform.googleapis.com/"
        f"v1beta1/projects/{settings.gcp_project_id}/locations/{settings.gcp_location}/"
        f"publishers/google/models/{settings.vertex_model_name}:generateContent"
    )
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0)) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
    if response.status_code != 200:
        _logger.error(
            "Vertex AI request failed: %s %s", response.status_code, response.text
        )
        raise RuntimeError("Vertex AI request failed")
    return response.json()


def _extract_text_from_candidate(candidate: dict[str, Any]) -> str:
    parts = candidate.get("content", {}).get("parts", [])
    texts: list[str] = []
    for part in parts:
        if "text" in part and part["text"]:
            texts.append(str(part["text"]))
        elif "json" in part and part["json"]:
            texts.append(str(part["json"]))
    combined = "\n".join(texts).strip()
    if combined:
        return combined
    raise ValueError("Unable to extract text response from Vertex AI.")


def _parse_claim_extraction_text(response_text: str) -> tuple[str | None, list[str]]:
    document_title: str | None = None
    claims: list[str] = []
    for raw_line in response_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("title:"):
            possible_title = line.split(":", 1)[1].strip()
            if possible_title and possible_title.lower() not in {"", "none", "n/a"}:
                document_title = possible_title
            continue
        if lowered.startswith("claims:"):
            continue
        if line.startswith("-"):
            claim_text = line[1:].strip()
            if claim_text:
                claims.append(claim_text)
            continue
    if not claims and response_text.strip():
        claims = [response_text.strip()]
    return document_title, claims


async def _run_vertex_request(
    prompt: str, response_schema: dict[str, Any] | None, stage_label: str
) -> str:
    print(f"[Vertex] {stage_label}: sending request.")
    payload = _build_request_payload(prompt, response_schema)
    response = await _post_to_vertex(payload)
    candidates = response.get("candidates") or []
    print(f"[Vertex] {stage_label}: received {len(candidates)} candidate(s).")
    if not candidates:
        raise RuntimeError("Vertex AI returned no candidates.")
    parsed_text = _extract_text_from_candidate(candidates[0])
    print(f"[Vertex] {stage_label}: extracted text response ({len(parsed_text)} chars).")
    return parsed_text


async def _extract_claim_statements(
    document_text: str,
) -> tuple[str | None, list[str], str]:
    prompt = _build_claim_extraction_prompt(document_text)
    response_text = await _run_vertex_request(prompt, None, "claim extraction")
    document_title, claims = _parse_claim_extraction_text(response_text)
    print(
        f"[Vertex] claim extraction: parsed {len(claims)} claim(s); "
        f"title={'present' if document_title else 'absent'}."
    )
    return document_title, claims, response_text


async def _verify_claim_statement(
    claim_statement: str,
    document_text: str,
    document_title: str | None,
    stage_label: str,
) -> str:
    prompt = _build_claim_verification_prompt(claim_statement, document_text, document_title)
    response_text = await _run_vertex_request(prompt, None, stage_label)
    return response_text


async def _verify_claim_with_logging(
    index: int,
    total_claims: int,
    statement: str,
    document_text: str,
    document_title: str | None,
    semaphore: asyncio.Semaphore,
) -> str:
    async with semaphore:
        stage_label = f"verification {index}/{total_claims}"
        print(f"[Vertex] {stage_label}: verifying claim -> {statement}")
        try:
            verification_text = await _verify_claim_statement(
                statement, document_text, document_title, stage_label
            )
            verification_text = verification_text.strip()
            print(
                f"[Vertex] {stage_label}: verification response length="
                f"{len(verification_text)}"
            )
            return (
                f"### Claim {index}\n"
                f"**Statement:** {statement}\n\n"
                f"{verification_text}"
            ).strip()
        except Exception as claim_exc:
            _logger.exception(
                "Failed to verify claim '%s': %s", statement, claim_exc
            )
            print(f"[Vertex] {stage_label}: verification failed -> {claim_exc}")
            return (
                f"### Claim {index}\n"
                f"**Statement:** {statement}\n\n"
                "Status: yellow\n"
                "Explanation: Verification failed due to an internal error.\n"
                "Citations: none"
            )


@retry(reraise=True, wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
async def extract_and_verify_claims(chunks: Sequence[str]) -> AnalysisResponse:
    if not chunks:
        return AnalysisResponse(document_title="Empty document", claims=[])

    try:
        document_text = _format_document_chunks(chunks)
        print("[Vertex] Starting two-stage claim analysis workflow.")
        document_title, claim_statements, extraction_markdown = await _extract_claim_statements(
            document_text
        )
        print(f"[Vertex] Extracted {len(claim_statements)} potential claims.")

        if not claim_statements:
            _logger.warning("Vertex AI returned no claims during extraction stage.")
            return AnalysisResponse(
                document_title=document_title or "Uploaded Document",
                claims=[],
                analysis_markdown=extraction_markdown.strip()
                if extraction_markdown.strip()
                else "No claims identified in the document.",
            )

        total_claims = len(claim_statements)
        semaphore = asyncio.Semaphore(_VERIFICATION_CONCURRENCY)
        verification_tasks = [
            asyncio.create_task(
                _verify_claim_with_logging(
                    index,
                    total_claims,
                    statement,
                    document_text,
                    document_title,
                    semaphore,
                )
            )
            for index, statement in enumerate(claim_statements, start=1)
        ]
        analysis_blocks = await asyncio.gather(*verification_tasks)

        if not analysis_blocks:
            _logger.warning(
                "Two-stage verification produced no claims despite extraction success."
            )
            return AnalysisResponse(
                document_title=document_title or "Uploaded Document",
                claims=[],
                analysis_markdown=(
                    "No verifications were generated despite successful extraction."
                ),
            )

        combined_analysis = "\n\n".join(analysis_blocks).strip()
        analysis_markdown = (
            f"# Document Analysis\n\n"
            f"**Title:** {document_title or 'Uploaded Document'}\n\n"
            "## Claim Extraction\n"
            f"{extraction_markdown.strip()}\n\n"
            "## Claim Verifications\n\n"
            f"{combined_analysis}"
        )

        return AnalysisResponse(
            document_title=document_title or "Uploaded Document",
            claims=[],
            analysis_markdown=analysis_markdown,
        )
    except Exception as exc:
        _logger.exception("Failed to process Vertex AI response: %s", exc)
        print(f"[Vertex] Two-stage claim analysis failed: {exc}")
        fallback_claim = Claim(
            statement="We could not verify claims for this document.",
            status=ClaimStatus.yellow,
            explanation="Vertex AI response could not be parsed.",
            citations=[],
        )
        fallback_markdown = (
            "# Document Analysis\n\n"
            "Analysis unavailable.\n\n"
            f"Reason: {exc}"
        )
        return AnalysisResponse(
            document_title="Verification unavailable",
            claims=[fallback_claim],
            analysis_markdown=fallback_markdown,
        )

