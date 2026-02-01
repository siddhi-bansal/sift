"use client";

/**
 * Static visual for "What is Sift?" — noise → filter → signal.
 * Left: scattered dots (noise). Center: aperture (purple). Right: single dot (signal).
 * No animation; complements the animated SignalDetector used at signup.
 */
export default function AboutVisual({
  className = "",
  size = 200,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <div
      className={`about-visual-graphic ${className}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg
        className="about-visual-graphic__svg"
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="av-ring" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.7" />
            <stop offset="100%" stopColor="var(--primary-dim)" stopOpacity="0.4" />
          </linearGradient>
        </defs>

        {/* Noise — left side: scattered dots (muted) */}
        <g fill="var(--muted)" opacity="0.8">
          <circle cx="22" cy="28" r="2.5" />
          <circle cx="18" cy="48" r="2" />
          <circle cx="28" cy="42" r="2" />
          <circle cx="14" cy="62" r="2.5" />
          <circle cx="32" cy="58" r="2" />
          <circle cx="24" cy="78" r="2" />
          <circle cx="16" cy="88" r="2" />
          <circle cx="30" cy="92" r="2" />
        </g>

        {/* Filter / aperture — center: concentric rings (purple) */}
        <circle
          cx="60"
          cy="60"
          r="28"
          stroke="url(#av-ring)"
          strokeWidth="2"
          fill="none"
          opacity="0.9"
        />
        <circle
          cx="60"
          cy="60"
          r="18"
          stroke="var(--primary)"
          strokeWidth="1.5"
          fill="none"
          opacity="0.6"
        />
        <circle cx="60" cy="60" r="8" fill="var(--primary)" opacity="0.25" />

        {/* Signal — right side: single bright dot (accent) */}
        <circle cx="98" cy="60" r="6" fill="var(--accent)" opacity="0.95" />
        <circle cx="98" cy="60" r="3" fill="var(--accent)" />
      </svg>
    </div>
  );
}
