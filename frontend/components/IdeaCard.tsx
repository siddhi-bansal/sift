"use client";

export type IdeaCardData = {
  id: string;
  title: string;
  summary: string;
  tag?: string;
};

export default function IdeaCard({ idea, snap = true }: { idea: IdeaCardData; snap?: boolean }) {
  return (
    <article
      className={`idea-card ${snap ? "idea-card--snap" : ""}`}
      style={{ minWidth: "280px", maxWidth: "320px" }}
    >
      {idea.tag && (
        <span className="idea-card__tag">{idea.tag}</span>
      )}
      <h3 className="idea-card__title">{idea.title}</h3>
      <p className="idea-card__summary">{idea.summary}</p>
    </article>
  );
}
