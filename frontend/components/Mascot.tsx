"use client";

/**
 * Legacy mascot (Sift uses SiftMark). Kept for reference.
 * Friendly blob with a magnifying glass — spotting signals and pain points.
 * Used sparingly (hero, loading, empty state).
 */
export default function Mascot({
  className = "",
  size = 160,
  animated = false,
}: {
  className?: string;
  size?: number;
  animated?: boolean;
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 160 160"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <defs>
        <linearGradient id="mascot-body" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.9} />
          <stop offset="100%" stopColor="#7c3aed" stopOpacity={0.95} />
        </linearGradient>
        <linearGradient id="mascot-accent" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#fbbf24" />
        </linearGradient>
        <filter id="mascot-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation={4} result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Main blob body — curious, rounded */}
      <ellipse
        cx={80}
        cy={88}
        rx={52}
        ry={56}
        fill="url(#mascot-body)"
        filter="url(#mascot-glow)"
        style={animated ? { animation: "mascot-float 3s ease-in-out infinite" } : undefined}
      />

      {/* Belly highlight */}
      <ellipse cx={78} cy={98} rx={28} ry={22} fill="rgba(255,255,255,0.2)" />

      {/* Eyes — big and curious */}
      <g style={animated ? { animation: "mascot-blink 4s ease-in-out infinite" } : undefined}>
        <ellipse cx={62} cy={78} rx={10} ry={12} fill="#1a1d24" />
        <ellipse cx={98} cy={78} rx={10} ry={12} fill="#1a1d24" />
        <ellipse cx={64} cy={76} rx={3} ry={4} fill="white" opacity={0.9} />
        <ellipse cx={100} cy={76} rx={3} ry={4} fill="white" opacity={0.9} />
      </g>

      {/* Magnifying glass — in front of right eye (drawn on top so it sits over the eye) */}
      <g transform="translate(98, 76)">
        <circle
          cx={0}
          cy={0}
          r={16}
          fill="none"
          stroke="url(#mascot-accent)"
          strokeWidth={4}
        />
        <line
          x1={10}
          y1={10}
          x2={22}
          y2={22}
          stroke="url(#mascot-accent)"
          strokeWidth={4}
          strokeLinecap="round"
        />
      </g>

      {/* Smile — friendly */}
      <path
        d="M 58 92 Q 80 102 102 92"
        stroke="#1a1d24"
        strokeWidth={3}
        strokeLinecap="round"
        fill="none"
      />

      {/* Little sparkles — "finding signals" */}
      <g fill="url(#mascot-accent)" opacity={0.9}>
        <circle cx={28} cy={62} r={2.5} />
        <circle cx={132} cy={72} r={2} />
        <circle cx={38} cy={118} r={2} />
      </g>
    </svg>
  );
}
