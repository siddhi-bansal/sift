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
      <h1>Unmet</h1>
      <p className="subtitle">
        Daily pain signals and industry catalysts for builders. We scan HN, Reddit, and news so you see complaints, unmet needs, and what’s changing.
      </p>

      {status === "success" ? (
        <div className="message success">{message}</div>
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
            />
          </div>
          <div className="form-group">
            <label>Interests (pick at least one)</label>
            <div className="interests-grid">
              {interests.map((i) => (
                <button
                  key={i.id}
                  type="button"
                  className={`interest-chip ${selected.has(i.id) ? "selected" : ""}`}
                  onClick={() => toggle(i.id)}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(i.id)}
                    readOnly
                    aria-hidden
                  />
                  {i.name}
                </button>
              ))}
            </div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={status === "loading"}>
            {status === "loading" ? "Signing up…" : "Subscribe"}
          </button>
          {message && status === "error" && (
            <div className="message error">{message}</div>
          )}
        </form>
      )}

      <p style={{ marginTop: "2rem", fontSize: "0.9rem", color: "var(--muted)" }}>
        <a href="/preview">Preview a past report</a>
      </p>
    </main>
  );
}
