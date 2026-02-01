"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { Issue } from "@/lib/email/types";
import { renderIssueEmailHtml } from "@/lib/email/renderIssueEmailHtml";
import MascotLoading from "@/components/MascotLoading";
import SignalDetector from "@/components/SignalDetector";

type Viewport = "desktop" | "mobile";

export default function EmailPreviewPage() {
  const params = useParams();
  const date = typeof params.date === "string" ? params.date : "";
  const [issue, setIssue] = useState<Issue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [viewport, setViewport] = useState<Viewport>("desktop");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!date || date.length !== 10) {
      setLoading(false);
      setError("Invalid date. Use YYYY-MM-DD.");
      return;
    }
    setLoading(true);
    setError("");
    fetch(`/api/issues/${date}`)
      .then((res) => {
        if (!res.ok) return res.json().then((b) => Promise.reject(new Error(b.error || res.statusText)));
        return res.json();
      })
      .then((data: Issue) => {
        setIssue(data);
      })
      .catch((e) => {
        setError(e.message || "Failed to load issue.");
        setIssue(null);
      })
      .finally(() => setLoading(false));
  }, [date]);

  const html = issue ? renderIssueEmailHtml(issue) : "";
  const iframeWidth = viewport === "desktop" ? 600 : 375;

  const copyHtml = useCallback(() => {
    if (!html) return;
    navigator.clipboard.writeText(html).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [html]);

  const downloadHtml = useCallback(() => {
    if (!html || !issue) return;
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sift-${issue.date}.html`;
    a.click();
    URL.revokeObjectURL(url);
  }, [html, issue]);

  return (
    <>
      <header className="nav-bar" role="banner">
        <div className="nav-bar__inner">
          <Link href="/" className="brand" aria-label="Sift home">
            <SignalDetector size={40} className="nav-bar__mark" />
            <div>
              <span className="masthead-title">Sift</span>
              <p className="masthead-tagline">Signal, not noise. Build what matters.</p>
            </div>
          </Link>
          <nav className="toplinks" aria-label="Main navigation">
            <Link href="/preview" className="toplinks__link toplinks__link--active">Preview</Link>
            <Link href="/" className="toplinks__link">Home</Link>
          </nav>
        </div>
      </header>

      <main className="container">
        <h1 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>
          Email preview {date && `— ${date}`}
        </h1>
        <p className="subtitle">
          Same HTML as the sent email. Toggle width or copy/download.
        </p>

        {loading && <MascotLoading message="Loading issue…" />}
        {error && !loading && (
          <div className="message error" role="alert">
            {error}
          </div>
        )}

        {issue && !loading && (
          <>
            <div className="card" style={{ marginBottom: "1rem", display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "center" }}>
              <span style={{ fontWeight: 600 }}>Viewport:</span>
              <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="viewport"
                  checked={viewport === "desktop"}
                  onChange={() => setViewport("desktop")}
                />
                Desktop (600px)
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", cursor: "pointer" }}>
                <input
                  type="radio"
                  name="viewport"
                  checked={viewport === "mobile"}
                  onChange={() => setViewport("mobile")}
                />
                Mobile (375px)
              </label>
              <button
                type="button"
                className="btn btn-primary"
                onClick={copyHtml}
                style={{ marginLeft: "auto" }}
              >
                {copied ? "Copied" : "Copy HTML"}
              </button>
              <button
                type="button"
                className="btn"
                onClick={downloadHtml}
              >
                Download .html
              </button>
            </div>

            <div
              style={{
                background: "#e0e0e0",
                padding: 16,
                borderRadius: "var(--radius-sm)",
                overflow: "auto",
              }}
            >
              <iframe
                title="Email preview"
                srcDoc={html}
                style={{
                  display: "block",
                  width: iframeWidth,
                  minHeight: 600,
                  border: "none",
                  backgroundColor: "#f5f5f5",
                  margin: "0 auto",
                }}
                sandbox="allow-same-origin"
              />
            </div>
          </>
        )}
      </main>
    </>
  );
}
