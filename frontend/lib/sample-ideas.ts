import type { IdeaCardData } from "@/components/IdeaCard";

/**
 * Sample idea cards for the homepage strip.
 * In production these could come from clusters (pain themes) via API.
 */
export const sampleIdeas: IdeaCardData[] = [
  {
    id: "1",
    title: "Dead-simple uptime monitoring",
    summary:
      "Teams want lightweight checks, not another observability platform. DevOps folks are building their own scripts because existing tools feel bloated.",
    tag: "Pain cluster",
  },
  {
    id: "2",
    title: "Local-first dev tooling",
    summary:
      "Developers keep asking for offline-first workflows and conflict-free sync. The cloud-only default is creating friction for distributed teams.",
    tag: "Rising",
  },
  {
    id: "3",
    title: "AI cost visibility",
    summary:
      "Founders are surprised by API bills. Simple usage dashboards and budget alerts for LLM/embedding calls would reduce anxiety and overruns.",
    tag: "Catalyst",
  },
  {
    id: "4",
    title: "One buildable wedge",
    summary:
      "Each issue surfaces one concrete wedge: a narrow, defensible angle you could build on. Not a market map — a single sharp opportunity.",
    tag: "Wedge",
  },
];
