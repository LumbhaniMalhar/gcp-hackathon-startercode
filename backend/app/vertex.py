from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

import httpx
from google.auth import default
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
from .schemas import AnalysisResponse, Claim, ClaimStatus, Citation

_logger = logging.getLogger(__name__)

_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)
_cached_credentials: Credentials | None = None


def _get_credentials() -> Credentials:
    global _cached_credentials
    if _cached_credentials is None:
        creds, _ = default(scopes=_SCOPES)
        _cached_credentials = creds
    if not _cached_credentials.valid:
        _cached_credentials.refresh(Request())
    return _cached_credentials


def _build_prompt(chunks: Sequence[str]) -> str:
    chunk_block = "\n\n---\n\n".join(chunk.strip() for chunk in chunks if chunk.strip())
    instructions = """You are an expert fact-checking agent participating in a grounded verification workflow.
You will be given the extracted text of a PDF document. Your task is to:
1. Identify the most significant factual claims, assertions, statistics, or concrete statements that could be checked.
2. For each claim, use the Google Search grounding tool to retrieve supporting or refuting evidence.
3. Classify each claim with one of three labels:
   - green: The claim is verified as accurate based on credible sources. Provide at least one citation.
   - yellow: No sufficient evidence was found to verify the claim. Provide an explanation and leave citations empty.
   - red: The claim is likely inaccurate or contradicted by evidence. Provide citations that refute the claim.
4. Return a strict JSON object that matches the following schema:
{
  "document_title": "<optional string title or null>",
  "claims": [
    {
      "statement": "<original claim text>",
      "status": "<green|yellow|red>",
      "explanation": "<short rationale>",
      "citations": [
        {
          "source": "<source title or domain>",
          "snippet": "<supporting or refuting quote>",
          "url": "<direct URL to the source>"
        }
      ]
    }
  ]
}
Respect the schema exactly. Do not include any additional fields. When citations are unavailable, return an empty array.
"""
    return f"{instructions}\n\nDocument text:\n{chunk_block}"


def _build_request_payload(prompt: str) -> dict[str, Any]:
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
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "topK": 40,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "document_title": {
                        "type": "STRING",
                        "nullable": True,
                    },
                    "claims": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "statement": {"type": "STRING"},
                                "status": {"type": "STRING"},
                                "explanation": {
                                    "type": "STRING",
                                    "nullable": True,
                                },
                                "citations": {
                                    "type": "ARRAY",
                                    "items": {
                                        "type": "OBJECT",
                                        "properties": {
                                            "source": {"type": "STRING"},
                                            "snippet": {
                                                "type": "STRING",
                                                "nullable": True,
                                            },
                                            "url": {
                                                "type": "STRING",
                                                "nullable": True,
                                            },
                                        },
                                        "required": ["source"],
                                    },
                                },
                            },
                            "required": ["statement", "status", "citations"],
                        },
                    },
                },
                "required": ["claims"],
            },
        },
        "tools": [
            {
                "googleSearch": {},
            }
        ],
    }


def _parse_claim_status(value: str) -> ClaimStatus:
    lowered = value.lower()
    if lowered in {"green", "verified"}:
        return ClaimStatus.green
    if lowered in {"yellow", "unknown", "unverified"}:
        return ClaimStatus.yellow
    if lowered in {"red", "inaccurate", "false"}:
        return ClaimStatus.red
    return ClaimStatus.yellow


def _parse_claims(payload: dict[str, Any]) -> AnalysisResponse:
    document_title = payload.get("document_title") or "Uploaded Document"
    claims_data = payload.get("claims", [])
    claims: list[Claim] = []
    for claim_data in claims_data:
        statement = claim_data.get("statement")
        status_raw = claim_data.get("status", "yellow")
        explanation = claim_data.get("explanation")
        citations_raw = claim_data.get("citations") or []
        if not statement:
            continue
        citations: list[Citation] = []
        for citation in citations_raw:
            source = citation.get("source") or citation.get("title") or "Unknown source"
            snippet = citation.get("snippet")
            url = citation.get("url")
            citations.append(Citation(source=source, snippet=snippet, url=url))
        claims.append(
            Claim(
                statement=statement,
                status=_parse_claim_status(status_raw),
                explanation=explanation,
                citations=citations,
            )
        )

    return AnalysisResponse(document_title=document_title, claims=claims)


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


def _extract_json_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    parts = candidate.get("content", {}).get("parts", [])
    for part in parts:
        if "json" in part:
            try:
                return json.loads(part["json"])
            except (TypeError, json.JSONDecodeError):
                continue
        text = (part.get("text") or "").strip()
        if not text:
            continue
        candidate_texts = [text]
        if text.startswith("```"):
            # Strip Markdown fences if present
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            candidate_texts.append("\n".join(lines).strip())
        for candidate_text in candidate_texts:
            if not candidate_text:
                continue
            try:
                return json.loads(candidate_text)
            except json.JSONDecodeError:
                continue
    raise ValueError("Unable to parse JSON response from Vertex AI.")


@retry(reraise=True, wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
async def extract_and_verify_claims(chunks: Sequence[str]) -> AnalysisResponse:
    if not chunks:
        return AnalysisResponse(document_title="Empty document", claims=[])

    prompt = _build_prompt(chunks)
    payload = _build_request_payload(prompt)

    try:
        response = await _post_to_vertex(payload)
        candidates = response.get("candidates") or []
        if not candidates:
            raise RuntimeError("Vertex AI returned no candidates.")
        print(candidates[0])
        parsed_payload = _extract_json_from_candidate(candidates[0])
        analysis = _parse_claims(parsed_payload)
        if not analysis.claims:
            _logger.warning("Vertex AI returned no claims; defaulting to empty response.")
            return AnalysisResponse(document_title=analysis.document_title, claims=[])
        return analysis
    except Exception as exc:
        _logger.exception("Failed to process Vertex AI response: %s", exc)
        fallback_claim = Claim(
            statement="We could not verify claims for this document.",
            status=ClaimStatus.yellow,
            explanation="Vertex AI response could not be parsed.",
            citations=[],
        )
        return AnalysisResponse(document_title="Verification unavailable", claims=[fallback_claim])

