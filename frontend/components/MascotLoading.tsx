"use client";

import Mascot from "./Mascot";

export default function MascotLoading({ message = "Finding signals…" }: { message?: string }) {
  return (
    <div className="mascot-loading">
      <div className="mascot-loading__mascot">
        <Mascot size={120} animated />
      </div>
      <p className="mascot-loading__text">{message}</p>
    </div>
  );
}
