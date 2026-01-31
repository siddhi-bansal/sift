"use client";

import Mascot from "./Mascot";

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
        <p className="hero-kicker">For builders & founders</p>
        <h1 className="hero-headline">
          Real problems.
          <br />
          Real opportunities.
        </h1>
        <p className="hero-lede">
          Daily pain signals and industry catalysts from Hacker News, Reddit, and tech — so you spot what to build next.
        </p>
        <a href="#signup" className="btn btn-primary">
          Get the digest
        </a>
      </div>
      <div className="hero-mascot-wrap">
        <div className="hero-mascot" aria-hidden>
          <Mascot size={240} animated />
        </div>
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
    </section>
  );
}
