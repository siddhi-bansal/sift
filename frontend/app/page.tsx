"use client";

import { useCallback, useEffect, useState } from "react";
import { supabase, type Interest } from "@/lib/supabase";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Home() {
  const [interests, setInterests] = useState<Interest[]>([]);
  const [email, setEmail] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const loadInterests = useCallback(async () => {
    const { data, error } = await supabase
      .from("interests")
      .select("id, name, description")
      .order("name");
    if (error) {
      console.error("interests", error);
      setInterests([]);
      return;
    }
    setInterests(data || []);
  }, []);

  useEffect(() => {
    loadInterests();
  }, [loadInterests]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");
    if (!EMAIL_RE.test(email.trim())) {
      setStatus("error");
      setMessage("Please enter a valid email.");
      return;
    }
    if (selected.size === 0) {
      setStatus("error");
      setMessage("Please pick at least one interest.");
      return;
    }
    setStatus("loading");
    const { data: sub, error: subErr } = await supabase
      .from("subscribers")
      .upsert({ email: email.trim().toLowerCase() }, { onConflict: "email" })
      .select("id")
      .single();
    if (subErr) {
      if (subErr.code === "23505") {
        setStatus("error");
        setMessage("This email is already subscribed.");
        return;
      }
      setStatus("error");
      setMessage(subErr.message || "Signup failed.");
      return;
    }
    const subscriberId = sub?.id;
    if (!subscriberId) {
      setStatus("error");
      setMessage("Could not create subscription.");
      return;
    }
    await supabase.from("subscriber_interests").delete().eq("subscriber_id", subscriberId);
    const rows = Array.from(selected).map((interest_id) => ({
      subscriber_id: subscriberId,
      interest_id,
    }));
    if (rows.length) {
      const { error: intErr } = await supabase.from("subscriber_interests").insert(rows);
      if (intErr) {
        setStatus("error");
        setMessage(intErr.message || "Failed to save interests.");
        return;
      }
    }
    setStatus("success");
    setMessage("You’re subscribed. We’ll use your interests to tailor the digest.");
  };

  return (
    <main className="container">
      <div className="header">
        <div className="brand">
          <img src="/unmet-logo.png" alt="Unmet" className="logo" />
          <div>
            <div className="masthead-title">Unmet</div>
            <div className="masthead-tagline">Signal-first newsletter</div>
          </div>
        </div>
        <div className="toplinks">
          <a href="/preview">Preview</a>
        </div>
      </div>

      <section className="layout">
        <div className="hero">
          <div className="kicker">FOR BUILDERS</div>
          <h1 className="headline">Real problems. Real opportunities.</h1>
          <p className="lede">
            Daily pain signals and industry catalysts from Hacker News, Reddit, and tech news.
          </p>

          <p style={{ maxWidth: "60ch", color: "var(--muted)", margin: "0 0 1.75rem" }}>
            Unmet scans thousands of posts daily to find recurring complaints, broken workflows, and new pressures created by industry changes.
          </p>

          <div className="section-title">What shows up in each issue:</div>
          <ul className="bullets">
            <li>Top pain clusters (with evidence)</li>
            <li>What’s rising</li>
            <li>Catalysts creating new problems</li>
            <li>One buildable wedge</li>
          </ul>

          <div className="divider" />

          <div className="sample" aria-label="Today’s sample signal">
            <div className="sample-label">Sample signal</div>
            <p>
              Teams want dead-simple uptime monitoring — not another observability platform.
            </p>
            <p>
              DevOps engineers are building their own scripts because existing tools feel bloated for basic uptime checks.
            </p>
            <p>
              <span style={{ color: "var(--muted-2)" }}>Possible wedge:</span> 5-minute setup monitoring with opinionated defaults.
            </p>
          </div>
        </div>

        <aside className="panel" aria-label="Signup">
          <h2>Get the digest</h2>
          <p className="hint">
            One email. Once a day.
          </p>

          {status === "success" ? (
            <div className="message success">{message}</div>
          ) : (
            <form onSubmit={submit}>
              <div className="form-group">
                <label htmlFor="email" style={{ fontFamily: "var(--font-mono)", letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "0.78rem" }}>
                  Email
                </label>
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
              <div className="form-group">
                <label style={{ fontFamily: "var(--font-mono)", letterSpacing: "0.08em", textTransform: "uppercase", fontSize: "0.78rem" }}>
                  Pick interests
                </label>
                <div className="interests-grid">
                  {interests.map((i) => (
                    <button
                      key={i.id}
                      type="button"
                      className={`interest-chip ${selected.has(i.id) ? "selected" : ""}`}
                      onClick={() => toggle(i.id)}
                      title={i.description ?? undefined}
                    >
                      <input type="checkbox" checked={selected.has(i.id)} readOnly aria-hidden />
                      <span>{i.name}</span>
                    </button>
                  ))}
                </div>
                <p className="hint" style={{ marginTop: "0.6rem" }}>Pick a few interests.</p>
              </div>
              <button type="submit" className="btn btn-primary" disabled={status === "loading"} style={{ width: "100%" }}>
                {status === "loading" ? "Subscribing…" : "Subscribe"}
              </button>
              {message && status === "error" && <div className="message error">{message}</div>}

              <div className="microcopy">No spam. Unsubscribe anytime.</div>

              <div style={{ marginTop: "0.9rem", color: "var(--muted-2)", fontSize: "0.92rem" }}>
                Want to see the format first? <a href="/preview">View a sample report</a>.
              </div>
            </form>
          )}
        </aside>
      </section>

      <div className="footerline" role="contentinfo" aria-label="Credibility">
        <span>
          <b>Built by builders.</b>
        </span>
        <span>Scans thousands of posts daily.</span>
      </div>
    </main>
  );
}
