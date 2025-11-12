export type ClaimStatus = "green" | "yellow" | "red";

export interface Citation {
  source: string;
  snippet?: string;
  url?: string;
}

export interface Claim {
  statement: string;
  status: ClaimStatus;
  explanation?: string;
  citations: Citation[];
}

export interface AnalysisResponse {
  document_title?: string;
  claims?: Claim[];
  analysis_markdown?: string;
}

