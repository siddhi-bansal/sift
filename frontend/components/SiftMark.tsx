"use client";

/**
 * Sift abstract mark: represents filtering and clarity.
 * Aperture/sieve motif — ring (filter) with center (signal). Minimal, calm, no character.
 */
export default function SiftMark({
  className = "",
  size = 48,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      {/* Outer ring — filter boundary */}
      <circle
        cx="24"
        cy="24"
        r="20"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        opacity="0.9"
      />
      {/* Inner ring — aperture */}
      <circle
        cx="24"
        cy="24"
        r="12"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        opacity="0.6"
      />
      {/* Center — signal through the filter */}
      <circle cx="24" cy="24" r="4" fill="currentColor" opacity="0.9" />
    </svg>
  );
}
