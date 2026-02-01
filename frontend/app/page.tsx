"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { sampleIdeas } from "@/lib/sample-ideas";
import Hero from "@/components/Hero";
import IdeaCardStrip from "@/components/IdeaCardStrip";
import SignalDetector from "@/components/SignalDetector";
import SiftMascot from "@/components/SiftMascot";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Home() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");
    if (!EMAIL_RE.test(email.trim())) {
      setStatus("error");
      setMessage("Please enter a valid email.");
      return;
    }
    setStatus("loading");
    const { error: subErr } = await supabase
      .from("subscribers")
      .upsert({ email: email.trim().toLowerCase() }, { onConflict: "email" });
    setStatus(subErr ? "error" : "success");
    if (subErr) {
      if (subErr.code === "23505") {
        setMessage("This email is already subscribed.");
        return;
      }
      setMessage(subErr.message || "Signup failed.");
      return;
    }
    setMessage("You're subscribed. We'll send you the digest.");
  };

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
            <a href="/preview">Preview</a>
          </nav>
        </div>
      </header>

      <main className="container">
        <Hero
          signup={{
            email,
            setEmail,
            status,
            message,
            onSubmit: submit,
          }}
        />

        <section className="about-section" aria-label="What is Sift">
          <div className="about-content">
            <h2 className="about-title">What is Sift?</h2>
            <p className="about-intro">
              The tech world is noisy. Most content isn&apos;t tied to real pain.
            </p>
            <p className="about-headline">
              What is an actual, recurring pain point worth building for?
            </p>
            <ul className="about-statements">
              <li>Sift scans Hacker News, Reddit, and tech news.</li>
              <li>We filter for recurring problems and surface evidence-backed signals.</li>
              <li>So you focus on what matters.</li>
            </ul>
          </div>
          <div className="about-visual" aria-hidden>
            <SignalDetector size={220} />
          </div>
        </section>

        <IdeaCardStrip
          ideas={sampleIdeas}
          title="What you get in each issue"
          subtitle="Themes, startup-grade idea cards, one bet. Every claim tied to evidence and links. No hype — just signal."
        />

        <section id="signup" className="signup-section" aria-label="Get the digest">
          <div className="signup-card-wrap">
            <div className="card card-signal">
              <h2>Get the digest</h2>
              <p className="hint">One email. Once a day. No spam.</p>

              {status === "success" ? (
                <div className="message success" role="status">
                  {message}
                </div>
              ) : (
                <form onSubmit={submit}>
                  <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input
                      id="email"
                      type="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      disabled={status === "loading"}
                      autoComplete="email"
                    />
                  </div>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={status === "loading"}
                    style={{ width: "100%" }}
                  >
                    {status === "loading" ? "Subscribing…" : "Subscribe"}
                  </button>
                  {message && status === "error" && (
                    <div className="message error" role="alert">
                      {message}
                    </div>
                  )}
                  <p className="microcopy">Unsubscribe anytime.</p>
                  <p style={{ marginTop: "0.75rem" }}>
                    <a href="/preview">View a sample issue</a> first.
                  </p>
                </form>
              )}
            </div>
          </div>
          <div className="signup-visual" aria-hidden>
            <SiftMascot size={200} />
          </div>
        </section>

        <footer className="footerline" role="contentinfo">
          <span>
            <b>Sift</b> — Signal, not noise. Build what matters.
          </span>
          <span>Scans developer conversations and tech news daily.</span>
        </footer>
      </main>
    </>
  );
}
