"use client";

import IdeaCard, { type IdeaCardData } from "./IdeaCard";

type Props = {
  ideas: IdeaCardData[];
  title?: string;
};

export default function IdeaCardStrip({ ideas, title = "Idea signals" }: Props) {
  if (ideas.length === 0) return null;

  return (
    <section className="idea-strip-section" aria-label={title}>
      <h2 className="idea-strip-title">{title}</h2>
      <div className="idea-strip-scroll">
        {ideas.map((idea) => (
          <IdeaCard key={idea.id} idea={idea} snap />
        ))}
      </div>
    </section>
  );
}
