"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import { supabase } from "@/lib/supabase";

export default function PreviewPage() {
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
    const { data, err } = await supabase
      .from("daily_reports")
      .select("markdown_content")
      .eq("date", d)
      .maybeSingle();
    setLoading(false);
    if (err) {
      setError(err.message || "Failed to load report.");
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
      <h1>Preview</h1>
      <p className="subtitle">View a daily report by date.</p>

      <div className="preview-date">
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

      {loading && <p style={{ color: "var(--muted)" }}>Loading…</p>}
      {error && !loading && <div className="message error">{error}</div>}
      {markdown && !loading && (
        <article className="prose">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </article>
      )}

      <p style={{ marginTop: "2rem", fontSize: "0.9rem", color: "var(--muted)" }}>
        <a href="/">Back to signup</a>
      </p>
    </main>
  );
}
