"use client";

import { Claim } from "@/types/claims";
import { analyzeDocument } from "@/lib/api";
import { ClaimCard } from "@/components/ClaimCard";
import React, { ChangeEvent, FormEvent, useMemo, useState } from "react";

type UploadState = "idle" | "loading" | "success" | "error";

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [documentTitle, setDocumentTitle] = useState<string | undefined>();

  const groupedClaims = useMemo(() => {
    return {
      green: claims.filter((claim) => claim.status === "green"),
      yellow: claims.filter((claim) => claim.status === "yellow"),
      red: claims.filter((claim) => claim.status === "red"),
    };
  }, [claims]);

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
    setClaims([]);

    try {
      const response = await analyzeDocument(file);
      setClaims(response.claims);
      setDocumentTitle(response.document_title);
      setUploadState("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error occurred");
      setUploadState("error");
    }
  };

  const statusOrder: Array<keyof typeof groupedClaims> = ["green", "yellow", "red"];

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
            Upload a PDF to extract key assertions, ground them with Vertex AI, and classify their
            accuracy.
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
            <p style={{ fontSize: "1.1rem", marginBottom: "0.75rem", fontWeight: 500 }}>
              Drag & drop a PDF here or click to browse
            </p>
            <p style={{ fontSize: "0.95rem", color: "rgba(148, 163, 184, 0.9)" }}>
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
            <p style={{ color: "#fca5a5", fontSize: "0.95rem", margin: 0 }}>{error}</p>
          )}

          {uploadState === "success" && claims.length === 0 && (
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
      </section>
    </main>
  );
}

