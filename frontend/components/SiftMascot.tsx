"use client";

import { useId } from "react";

/**
 * Cute animated mascot for Sift — optimistic blob with magnifying glass.
 * Float + sparkle animations; respects reduced-motion via global override.
 */
export default function SiftMascot({
  className = "",
  size = 180,
}: {
  className?: string;
  size?: number;
}) {
  const id = useId().replace(/:/g, "");
  return (
    <div
      className={`sift-mascot ${className}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg
        className="sift-mascot__svg"
        viewBox="0 0 160 160"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id={`sm-body-${id}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.95} />
            <stop offset="100%" stopColor="var(--primary-dim)" stopOpacity={0.9} />
          </linearGradient>
          <linearGradient id={`sm-accent-${id}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--accent)" />
            <stop offset="100%" stopColor="var(--accent-dim)" />
          </linearGradient>
          <filter id={`sm-glow-${id}`} x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation={3} result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Blob body — gentle float */}
        <g className="sift-mascot__float">
          <ellipse
            cx={80}
            cy={88}
            rx={52}
            ry={56}
            fill={`url(#sm-body-${id})`}
            filter={`url(#sm-glow-${id})`}
          />
          <ellipse cx={78} cy={98} rx={28} ry={22} fill="rgba(255,255,255,0.18)" />
        </g>

        {/* Eyes — optimistic, looking up slightly */}
        <g>
          <ellipse cx={62} cy={76} rx={10} ry={12} fill="#1a1d24" />
          <ellipse cx={98} cy={76} rx={10} ry={12} fill="#1a1d24" />
          <ellipse cx={64} cy={74} rx={3} ry={4} fill="white" opacity={0.95} />
          <ellipse cx={100} cy={74} rx={3} ry={4} fill="white" opacity={0.95} />
        </g>

        {/* Magnifying glass — finding signal */}
        <g transform="translate(98, 74)">
          <circle cx={0} cy={0} r={16} fill="none" stroke={`url(#sm-accent-${id})`} strokeWidth={4} />
          <line x1={10} y1={10} x2={22} y2={22} stroke={`url(#sm-accent-${id})`} strokeWidth={4} strokeLinecap="round" />
        </g>

        {/* Smile — friendly, upturned */}
        <path
          d="M 58 90 Q 80 102 102 90"
          stroke="#1a1d24"
          strokeWidth={2.5}
          strokeLinecap="round"
          fill="none"
        />

        {/* Sparkles — twinkle */}
        <g className="sift-mascot__sparkle" fill="var(--accent)">
          <circle cx={28} cy={62} r={2.5} opacity={0.9} />
          <circle cx={132} cy={68} r={2} opacity={0.85} />
          <circle cx={38} cy={118} r={2} opacity={0.9} />
        </g>
      </svg>
    </div>
  );
}
