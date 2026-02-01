import type { IdeaCardData } from "@/components/IdeaCard";

/**
 * What actually shows up in each Sift issue (matches backend report structure).
 */
export const sampleIdeas: IdeaCardData[] = [
  {
    id: "1",
    title: "Today's themes",
    summary: "One line of recurring pain themes from the day.",
    tag: "Themes",
  },
  {
    id: "2",
    title: "Startup-Grade Idea Cards",
    summary: "2–3 buildable ideas with problem, evidence, wedge, and kill criteria.",
    tag: "Cards",
  },
  {
    id: "3",
    title: "One bet",
    summary: "Single sentence we'd bet on for the day.",
    tag: "Bet",
  },
  {
    id: "4",
    title: "Evidence-first",
    summary: "Every claim tied to snippets and links. No invented names or leaps.",
    tag: "Intro",
  },
];
