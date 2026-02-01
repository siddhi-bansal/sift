"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { sampleIdeas } from "@/lib/sample-ideas";
import Hero from "@/components/Hero";
import IdeaCardStrip from "@/components/IdeaCardStrip";

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
          <a href="/" className="brand" aria-label="Unmet home">
            <img src="/unmet-logo.png" alt="" className="logo" />
            <div>
              <span className="masthead-title">Unmet</span>
              <p className="masthead-tagline">Signal-first newsletter</p>
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

        <IdeaCardStrip
          ideas={sampleIdeas}
          title="What shows up in each issue"
          subtitle="Themes, startup-grade cards, one bet. Every claim tied to evidence."
        />

        <section id="signup" className="panel" aria-label="Get the digest">
          <div className="card">
            <h2>Get the digest</h2>
            <p className="hint">One email. Once a day.</p>

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
                <p className="microcopy">No spam. Unsubscribe anytime.</p>
                <p style={{ marginTop: "0.75rem" }}>
                  <a href="/preview">View a sample report</a> first.
                </p>
              </form>
            )}
          </div>
        </section>

        <footer className="footerline" role="contentinfo">
          <span>
            <b>Built by builders.</b>
          </span>
          <span>Scans thousands of posts daily.</span>
        </footer>
      </main>
    </>
  );
}
