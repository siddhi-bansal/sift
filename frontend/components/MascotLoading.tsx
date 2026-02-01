"use client";

import SignalDetector from "./SignalDetector";

export default function MascotLoading({ message = "Finding signals…" }: { message?: string }) {
  return (
    <div className="mascot-loading">
      <div className="mascot-loading__mark">
        <SignalDetector size={80} />
      </div>
      <p className="mascot-loading__text">{message}</p>
    </div>
  );
}
