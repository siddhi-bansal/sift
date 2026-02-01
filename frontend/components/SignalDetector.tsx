"use client";

/**
 * Signal detector visual for "What is Sift?" — focus target, not decoration.
 * Purple/yellow on dark; slow pulsing rings, gentle orbit, breathing glow.
 * Motion is calm and premium; respects prefers-reduced-motion.
 */
export default function SignalDetector({
  className = "",
  size = 200,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <div
      className={`signal-detector ${className}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg
        className="signal-detector__svg"
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="sd-ring" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.6" />
            <stop offset="100%" stopColor="var(--primary-dim)" stopOpacity="0.35" />
          </linearGradient>
          <radialGradient id="sd-core" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="1" />
            <stop offset="70%" stopColor="var(--accent)" stopOpacity="0.5" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </radialGradient>
          <filter id="sd-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Outer ring — pulse (slow) */}
        <circle
          className="signal-detector__ring signal-detector__ring--outer"
          cx="60"
          cy="60"
          r="52"
          stroke="url(#sd-ring)"
          strokeWidth="1.5"
          fill="none"
        />
        {/* Middle ring — pulse offset */}
        <circle
          className="signal-detector__ring signal-detector__ring--mid"
          cx="60"
          cy="60"
          r="38"
          stroke="url(#sd-ring)"
          strokeWidth="1"
          fill="none"
          opacity="0.8"
        />
        {/* Inner ring — aperture */}
        <circle
          className="signal-detector__ring signal-detector__ring--inner"
          cx="60"
          cy="60"
          r="24"
          stroke="var(--primary)"
          strokeWidth="1"
          fill="none"
          opacity="0.5"
        />

        {/* Orbiting dots — signal points */}
        <g className="signal-detector__orbit">
          <circle cx="60" cy="8" r="2.5" fill="var(--accent)" opacity="0.9" />
          <circle cx="60" cy="112" r="2" fill="var(--accent)" opacity="0.7" />
          <circle cx="8" cy="60" r="2" fill="var(--accent)" opacity="0.7" />
          <circle cx="112" cy="60" r="2.5" fill="var(--accent)" opacity="0.9" />
          <circle cx="92" cy="28" r="1.5" fill="var(--accent)" opacity="0.6" />
          <circle cx="28" cy="92" r="1.5" fill="var(--accent)" opacity="0.6" />
        </g>

        {/* Core — signal through the filter; breathing glow */}
        <circle
          className="signal-detector__core"
          cx="60"
          cy="60"
          r="8"
          fill="url(#sd-core)"
          filter="url(#sd-glow)"
        />
        <circle
          className="signal-detector__core-dot"
          cx="60"
          cy="60"
          r="4"
          fill="var(--accent)"
        />
      </svg>
    </div>
  );
}
