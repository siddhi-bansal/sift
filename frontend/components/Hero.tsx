"use client";

import SiftMascot from "./SiftMascot";

type SignupProps = {
  email: string;
  setEmail: (v: string) => void;
  status: "idle" | "loading" | "success" | "error";
  message: string;
  onSubmit: (e: React.FormEvent) => void;
};

export default function Hero({
  signup,
}: {
  signup?: SignupProps | null;
}) {
  return (
    <section className="hero-section" aria-label="Welcome">
      <div className="hero-content">
        <p className="hero-kicker">For founders & developers</p>
        <h1 className="hero-headline">
          <span className="hero-headline__line">Signal, not noise.</span>
          <span className="hero-headline__line">Build what matters.</span>
        </h1>
        <p className="hero-lede">
        Sift scans developer conversations and tech news to filter noise and surface repeated, evidence-backed signals — so you can focus on building what matters.
        </p>
      </div>
      <div className="hero-cta-wrap">
        {signup && (
          <div className="hero-signup" aria-label="Sign up">
            {signup.status === "success" ? (
              <p className="hero-signup__success">{signup.message}</p>
            ) : (
              <form onSubmit={signup.onSubmit} className="hero-signup__form">
                <label htmlFor="hero-email" className="hero-signup__label">
                  Get the digest
                </label>
                <input
                  id="hero-email"
                  type="email"
                  placeholder="you@example.com"
                  value={signup.email}
                  onChange={(e) => signup.setEmail(e.target.value)}
                  disabled={signup.status === "loading"}
                  autoComplete="email"
                  className="hero-signup__input"
                />
                <button
                  type="submit"
                  className="btn btn-primary hero-signup__btn"
                  disabled={signup.status === "loading"}
                >
                  {signup.status === "loading" ? "…" : "Subscribe"}
                </button>
                {signup.message && signup.status === "error" && (
                  <p className="hero-signup__error" role="alert">
                    {signup.message}
                  </p>
                )}
              </form>
            )}
          </div>
        )}
      </div>
      <div className="hero-mark-wrap">
        <div className="hero-mark" aria-hidden>
          <SiftMascot size={200} />
        </div>
      </div>
    </section>
  );
}
