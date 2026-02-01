"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { supabase } from "@/lib/supabase";
import MascotLoading from "@/components/MascotLoading";
import SignalDetector from "@/components/SignalDetector";
import DatePicker from "@/components/DatePicker";

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
    <>
      <header className="nav-bar" role="banner">
        <div className="nav-bar__inner">
          <a href="/" className="brand" aria-label="Sift home">
            <SignalDetector size={40} className="nav-bar__mark" />
            <div>
              <span className="masthead-title">Sift</span>
              <p className="masthead-tagline">Signal, not noise. Build what matters.</p>
            </div>
          </a>
          <nav className="toplinks" aria-label="Main navigation">
            <a href="/preview" className="toplinks__link toplinks__link--active">Preview</a>
            <a href="/" className="toplinks__link">Home</a>
          </nav>
        </div>
      </header>

      <main className="container">
        <h1 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>Preview</h1>
        <p className="subtitle">Pick a date to load that day&apos;s report.</p>

        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <div className="preview-date" style={{ marginBottom: 0 }}>
            <label htmlFor="date">Date</label>
            <DatePicker id="date" value={date} onChange={setDate} />
            <button type="button" className="btn btn-primary" onClick={go}>
              Load
            </button>
          </div>
        </div>

        {loading && <MascotLoading message="Finding that report…" />}
        {error && !loading && (
          <div className="message error" role="alert">
            {error}
          </div>
        )}
        {markdown && !loading && (
          <>
            <div className="card" style={{ marginBottom: "1rem" }}>
              <Link href={`/preview/email/${date}`} className="btn btn-primary">
                View Email Preview
              </Link>
            </div>
            <article className="prose card">
              <ReactMarkdown>{markdown}</ReactMarkdown>
            </article>
          </>
        )}
      </main>
    </>
  );
}

export default function PreviewPage() {
  return (
    <Suspense
      fallback={
        <>
          <header className="nav-bar" role="banner">
            <div className="nav-bar__inner">
              <span className="masthead-title">Sift</span>
            </div>
          </header>
          <main className="container">
            <MascotLoading message="Loading preview…" />
          </main>
        </>
      }
    >
      <PreviewInner />
    </Suspense>
  );
}
