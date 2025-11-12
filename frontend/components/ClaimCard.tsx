import { Claim, ClaimStatus } from "@/types/claims";
import React from "react";

const statusConfig: Record<
  ClaimStatus,
  { border: string; badgeBg: string; badgeText: string; label: string }
> = {
  green: {
    border: "#22c55e",
    badgeBg: "rgba(34, 197, 94, 0.15)",
    badgeText: "#4ade80",
    label: "Verified",
  },
  yellow: {
    border: "#facc15",
    badgeBg: "rgba(250, 204, 21, 0.15)",
    badgeText: "#fde68a",
    label: "Unverified",
  },
  red: {
    border: "#f87171",
    badgeBg: "rgba(248, 113, 113, 0.15)",
    badgeText: "#fca5a5",
    label: "Inaccurate",
  },
};

type ClaimCardProps = {
  claim: Claim;
};

export function ClaimCard({ claim }: ClaimCardProps) {
  const config = statusConfig[claim.status];

  return (
    <article
      style={{
        border: `1px solid ${config.border}`,
        borderRadius: "16px",
        padding: "1.5rem",
        background:
          "linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.95) 100%)",
        boxShadow: "0 12px 30px rgba(15, 23, 42, 0.4)",
        display: "flex",
        flexDirection: "column",
        gap: "0.75rem",
      }}
    >
      <div
        style={{
          alignSelf: "flex-start",
          borderRadius: "9999px",
          backgroundColor: config.badgeBg,
          color: config.badgeText,
          padding: "0.25rem 0.75rem",
          fontWeight: 600,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
          fontSize: "0.75rem",
        }}
      >
        {config.label}
      </div>

      <p style={{ fontSize: "1.05rem", lineHeight: 1.6 }}>{claim.statement}</p>

      {claim.explanation && (
        <p style={{ fontSize: "0.95rem", color: "#94a3b8" }}>
          {claim.explanation}
        </p>
      )}

      {claim.citations.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <span style={{ fontSize: "0.85rem", color: "#cbd5f5", opacity: 0.8 }}>
            Citations
          </span>
          <ul
            style={{
              listStyle: "none",
              padding: 0,
              margin: 0,
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
          >
            {claim.citations.map((citation, index) => (
              <li
                key={`${citation.source}-${index}`}
                style={{
                  backgroundColor: "rgba(148, 163, 184, 0.1)",
                  borderRadius: "12px",
                  padding: "0.75rem",
                }}
              >
                <p style={{ margin: 0, fontWeight: 600 }}>{citation.source}</p>
                {citation.snippet && (
                  <p style={{ margin: "0.35rem 0 0", fontSize: "0.85rem" }}>
                    {citation.snippet}
                  </p>
                )}
                {citation.url && (
                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      marginTop: "0.35rem",
                      display: "inline-block",
                      fontSize: "0.85rem",
                      color: "#60a5fa",
                    }}
                  >
                    View source
                  </a>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}

