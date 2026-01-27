"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { supabase } from "@/lib/supabase";

function PreviewInner() {
  const searchParams = useSearchParams();
  const queryDate = searchParams.get("date") || "";
  const [date, setDate] = useState(queryDate || new Date().toISOString().slice(0, 10));
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchReport = useCallback(async (d: string) => {
    if (!d || d.length !== 10) {
      setMarkdown(null);
      setError("Use a date like YYYY-MM-DD");
      return;
    }
    setLoading(true);
    setError("");
    const { data, error } = await supabase
      .from("daily_reports")
      .select("markdown_content")
      .eq("date", d)
      .maybeSingle();
    setLoading(false);
    if (error) {
      setError(error.message || "Failed to load report.");
      setMarkdown(null);
      return;
    }
    setMarkdown(data?.markdown_content ?? null);
    if (!data?.markdown_content) setError("No report for this date.");
  }, []);

  useEffect(() => {
    if (queryDate) {
      setDate(queryDate);
      fetchReport(queryDate);
    }
  }, [queryDate, fetchReport]);

  const go = () => fetchReport(date);

  return (
    <main className="container">
      <div className="header">
        <div className="brand">
          <div className="logo" aria-hidden />
          <div>
            <div style={{ fontWeight: 700, fontSize: "1.05rem", lineHeight: 1.1 }}>Unmet</div>
            <div style={{ color: "var(--muted-2)", fontSize: "0.9rem" }}>Report preview</div>
          </div>
        </div>
        <div className="toplinks">
          <a href="/">Signup</a>
        </div>
      </div>

      <h1 style={{ marginTop: 0 }}>Preview</h1>
      <p className="subtitle">Pick a date to load that day’s report.</p>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div className="preview-date" style={{ marginBottom: 0 }}>
        <label htmlFor="date">Date</label>
        <input
          id="date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <button type="button" className="btn btn-primary" onClick={go} style={{ marginLeft: "0.5rem" }}>
          Load
        </button>
      </div>
      </div>

      {loading && <p style={{ color: "var(--muted)" }}>Loading…</p>}
      {error && !loading && <div className="message error">{error}</div>}
      {markdown && !loading && (
        <article className="prose card">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </article>
      )}
    </main>
  );
}

export default function PreviewPage() {
  return (
    <Suspense fallback={<main className="container"><p style={{ color: "var(--muted)" }}>Loading preview…</p></main>}>
      <PreviewInner />
    </Suspense>
  );
}
