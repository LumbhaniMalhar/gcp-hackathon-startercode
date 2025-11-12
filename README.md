# Agentic Claims Verifier

End-to-end FastAPI + Next.js application that ingests PDF documents, extracts factual claims, and verifies them using Google Vertex AI Gemini with grounded web search. Each claim is scored as:

- **Green** &mdash; Verified by grounded sources
- **Yellow** &mdash; Insufficient evidence found
- **Red** &mdash; Contradicted by grounded sources

## Architecture

- **Backend** (`backend/`): FastAPI service that handles PDF uploads, text extraction via `pypdf`, and fact-check orchestration through Vertex AI's Gemini models.
- **Frontend** (`frontend/`): Next.js App Router UI with drag-and-drop PDF upload and color-coded claim visualizations.
- **Google Vertex AI**: Gemini 1.5 Pro with Google Search grounding for retrieval-augmented verification and citation generation.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud project with Vertex AI GenAI APIs enabled
- Service account with `Vertex AI User` and `aiplatform.endpoints.predict` permissions

## Environment Configuration

Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `GCP_LOCATION`: Vertex AI region (e.g., `us-central1`)
- `VERTEX_MODEL_NAME`: Gemini model (e.g., `gemini-1.5-pro`)
- `GOOGLE_APPLICATION_CREDENTIALS`: Absolute path to service account key JSON
- `NEXT_PUBLIC_API_BASE_URL`: Base URL for FastAPI (defaults to `http://localhost:8000`)

Export `GOOGLE_APPLICATION_CREDENTIALS` for local runs if the file is not in the default path:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API exposes:

- `GET /health` &mdash; basic status endpoint
- `POST /api/analyze` &mdash; accepts a `multipart/form-data` upload with a `file` field containing a PDF

Response schema (`application/json`):

```json
{
  "document_title": "string|null",
  "claims": [
    {
      "statement": "string",
      "status": "green|yellow|red",
      "explanation": "string|null",
      "citations": [
        {
          "source": "string",
          "snippet": "string|null",
          "url": "string|null"
        }
      ]
    }
  ]
}
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:3000` (configurable via Next.js environment variables). It proxies requests directly to the FastAPI backend configured via `NEXT_PUBLIC_API_BASE_URL`.

## Vertex AI Notes

- The backend uses the Vertex AI REST endpoint `:generateContent` with Google Search grounding enabled.
- Ensure the Gemini model you select is available in your region and project.
- Grounding citations depend on the model returning metadata &mdash; the app gracefully degrades to yellow status when evidence is unavailable or the API response cannot be parsed.

## Development Scripts

- `backend`: Run `ruff` or `black` if you add them to the Python environment.
- `frontend`: `npm run lint` (Next.js ESLint rules).

## Next Steps

- Add persistent storage for historical analyses.
- Implement authentication and usage quotas.
- Expand document extraction to handle OCR (scanned PDFs) via Google Document AI.

