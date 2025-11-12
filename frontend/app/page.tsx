"use client";

import { analyzeDocument } from "@/lib/api";
import React, { ChangeEvent, FormEvent, useState } from "react";
import ReactMarkdown from "react-markdown";

type UploadState = "idle" | "loading" | "success" | "error";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  // const [claims, setClaims] = useState<Claim[]>([]);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [documentTitle, setDocumentTitle] = useState<string | undefined>();
  const [analysisMarkdown, setAnalysisMarkdown] = useState<string>("");
  // const groupedClaims = useMemo(() => {
  //   return {
  //     green: claims.filter((claim) => claim.status === "green"),
  //     yellow: claims.filter((claim) => claim.status === "yellow"),
  //     red: claims.filter((claim) => claim.status === "red"),
  //   };
  // }, [claims]);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (selected && !selected.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      setFile(null);
      event.target.value = "";
      return;
    }
    setError(null);
    setFile(selected ?? null);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError("Please select a PDF document to analyze.");
      return;
    }
    setUploadState("loading");
    setError(null);
    // setClaims([]);
    setAnalysisMarkdown("");

    try {
      const response = await analyzeDocument(file);
      // setClaims(response.claims ?? []);
      setDocumentTitle(response.document_title);
      setAnalysisMarkdown(response.analysis_markdown ?? "");
      setUploadState("success");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unexpected error occurred"
      );
      setUploadState("error");
    }
  };

  // const statusOrder: Array<keyof typeof groupedClaims> = ["green", "yellow", "red"];

  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        padding: "3rem 1.5rem",
      }}
    >
      <section
        style={{
          maxWidth: "960px",
          width: "100%",
          margin: "0 auto",
          display: "flex",
          flexDirection: "column",
          gap: "2rem",
        }}
      >
        <header style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: "2.75rem", marginBottom: "0.5rem" }}>
            Agentic Claims Verifier
          </h1>
          <p style={{ fontSize: "1.05rem", color: "#cbd5f5" }}>
            Upload a PDF to extract key assertions, ground them with Vertex AI,
            and classify their accuracy.
          </p>
        </header>

        <form
          onSubmit={onSubmit}
          style={{
            background:
              "linear-gradient(180deg, rgba(15,23,42,0.8) 0%, rgba(30,41,59,0.95) 100%)",
            borderRadius: "24px",
            padding: "2.5rem",
            border: "1px solid rgba(148, 163, 184, 0.25)",
            boxShadow: "0 16px 40px rgba(15, 23, 42, 0.45)",
            display: "flex",
            flexDirection: "column",
            gap: "1.5rem",
          }}
        >
          <label
            htmlFor="document-upload"
            style={{
              border: "2px dashed rgba(148, 163, 184, 0.4)",
              borderRadius: "16px",
              padding: "2rem",
              textAlign: "center",
              cursor: "pointer",
              transition: "border-color 0.2s ease",
            }}
          >
            <input
              id="document-upload"
              type="file"
              accept="application/pdf"
              onChange={onFileChange}
              style={{ display: "none" }}
            />
            <p
              style={{
                fontSize: "1.1rem",
                marginBottom: "0.75rem",
                fontWeight: 500,
              }}
            >
              Drag & drop a PDF here or click to browse
            </p>
            <p
              style={{ fontSize: "0.95rem", color: "rgba(148, 163, 184, 0.9)" }}
            >
              Max file size 15MB. PDFs only.
            </p>
            {file && (
              <p style={{ marginTop: "1rem", color: "#38bdf8" }}>
                Selected: <strong>{file.name}</strong>
              </p>
            )}
          </label>

          <button
            type="submit"
            disabled={uploadState === "loading"}
            style={{
              padding: "0.95rem 1.75rem",
              borderRadius: "999px",
              border: "none",
              fontSize: "1rem",
              fontWeight: 600,
              color: "#0f172a",
              background: uploadState === "loading" ? "#94a3b8" : "#38bdf8",
              cursor: uploadState === "loading" ? "not-allowed" : "pointer",
              transition: "transform 0.1s ease",
            }}
          >
            {uploadState === "loading" ? "Analyzing..." : "Analyze document"}
          </button>

          {error && (
            <p style={{ color: "#fca5a5", fontSize: "0.95rem", margin: 0 }}>
              {error}
            </p>
          )}

          {uploadState === "success" && !analysisMarkdown && (
            <p style={{ color: "#cbd5f5" }}>
              No claims detected. Try another document or adjust the content.
            </p>
          )}
        </form>

        {uploadState === "loading" && (
          <div
            style={{
              textAlign: "center",
              color: "#cbd5f5",
              fontSize: "1rem",
              padding: "1rem",
            }}
          >
            Running extraction and verification with Vertex AI...
          </div>
        )}

        {/* Legacy JSON-based claim rendering preserved for future reference.
        {claims.length > 0 && (
          <section style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <header>
              <h2 style={{ margin: 0, fontSize: "1.8rem" }}>
                Verification report {documentTitle ? `for “${documentTitle}”` : ""}
              </h2>
              <p style={{ margin: "0.5rem 0 0", color: "#cbd5f5" }}>
                Claims are grouped by verification status with supporting citations when available.
              </p>
            </header>

            {statusOrder
              .filter((status) => groupedClaims[status].length > 0)
              .map((status) => (
                <section key={status} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <h3 style={{ margin: 0, fontSize: "1.4rem", textTransform: "capitalize" }}>
                    {status}
                  </h3>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                      gap: "1.25rem",
                    }}
                  >
                    {groupedClaims[status].map((claim) => (
                      <ClaimCard key={claim.statement} claim={claim} />
                    ))}
                  </div>
                </section>
              ))}
          </section>
        )}
        */}

        {analysisMarkdown && (
          <section
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "1.5rem",
              background: "rgba(15,23,42,0.6)",
              borderRadius: "24px",
              padding: "2.5rem",
              border: "1px solid rgba(148, 163, 184, 0.25)",
              boxShadow: "0 16px 40px rgba(15, 23, 42, 0.45)",
            }}
          >
            <header>
              <h2 style={{ margin: 0, fontSize: "1.8rem" }}>
                Analysis report {documentTitle ? `for “${documentTitle}”` : ""}
              </h2>
              <p style={{ margin: "0.5rem 0 0", color: "#cbd5f5" }}>
                The response below is rendered directly from the Vertex AI
                Markdown output.
              </p>
            </header>
            <div
              style={{
                padding: "1.5rem",
                borderRadius: "16px",
                background: "rgba(30, 41, 59, 0.65)",
                border: "1px solid rgba(148, 163, 184, 0.25)",
                overflowX: "auto",
              }}
            >
              <ReactMarkdown
                components={{
                  h1: ({ node, ...props }) => (
                    <h1
                      style={{
                        fontSize: "2rem",
                        marginBottom: "1rem",
                        color: "#e2e8f0",
                      }}
                      {...props}
                    />
                  ),
                  h2: ({ node, ...props }) => (
                    <h2
                      style={{
                        fontSize: "1.6rem",
                        marginTop: "1.5rem",
                        marginBottom: "0.75rem",
                        color: "#f1f5f9",
                      }}
                      {...props}
                    />
                  ),
                  h3: ({ node, ...props }) => (
                    <h3
                      style={{
                        fontSize: "1.3rem",
                        marginTop: "1.25rem",
                        marginBottom: "0.5rem",
                        color: "#f8fafc",
                      }}
                      {...props}
                    />
                  ),
                  p: ({ node, ...props }) => (
                    <p
                      style={{
                        marginBottom: "0.75rem",
                        lineHeight: 1.6,
                        color: "#cbd5f5",
                      }}
                      {...props}
                    />
                  ),
                  ul: ({ node, ...props }) => (
                    <ul
                      style={{
                        paddingLeft: "1.5rem",
                        marginBottom: "0.75rem",
                      }}
                      {...props}
                    />
                  ),
                  li: ({ node, ...props }) => (
                    <li
                      style={{
                        marginBottom: "0.4rem",
                        color: "#cbd5f5",
                      }}
                      {...props}
                    />
                  ),
                  strong: ({ node, ...props }) => (
                    <strong style={{ color: "#f8fafc" }} {...props} />
                  ),
                }}
              >
                {analysisMarkdown}
              </ReactMarkdown>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}

