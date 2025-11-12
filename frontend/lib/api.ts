import { AnalysisResponse } from "@/types/claims";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function analyzeDocument(file: File): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new Error(error.detail ?? "Failed to analyze document");
  }

  return (await response.json()) as AnalysisResponse;
}

