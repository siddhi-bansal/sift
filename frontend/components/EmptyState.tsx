"use client";

import Mascot from "./Mascot";

type Props = {
  title: string;
  description?: string;
  action?: React.ReactNode;
};

export default function EmptyState({ title, description, action }: Props) {
  return (
    <div className="empty-state">
      <div className="empty-state__mascot">
        <Mascot size={140} animated />
      </div>
      <h2 className="empty-state__title">{title}</h2>
      {description && <p className="empty-state__desc">{description}</p>}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}
