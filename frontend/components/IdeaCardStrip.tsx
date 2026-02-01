"use client";

import IdeaCard, { type IdeaCardData } from "./IdeaCard";

type Props = {
  ideas: IdeaCardData[];
  title?: string;
  subtitle?: string;
};

export default function IdeaCardStrip({ ideas, title = "Idea signals", subtitle }: Props) {
  if (ideas.length === 0) return null;

  return (
    <section className="idea-strip-section" aria-label={title}>
      <div className="idea-strip-header">
        <h2 className="idea-strip-title">{title}</h2>
        {subtitle && <p className="idea-strip-subtitle">{subtitle}</p>}
      </div>
      <div className="idea-strip-grid">
        {ideas.map((idea) => (
          <IdeaCard key={idea.id} idea={idea} snap={false} />
        ))}
      </div>
    </section>
  );
}
