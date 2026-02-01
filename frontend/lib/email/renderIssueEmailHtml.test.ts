/**
 * Assert that renderIssueEmailHtml output contains no raw markdown tokens (##, **, `).
 * Run: npx vitest run lib/email/renderIssueEmailHtml.test.ts
 * Or: npm test
 */

import { describe, it, expect } from "vitest";
import type { Issue } from "./types";
import { renderIssueEmailHtml } from "./renderIssueEmailHtml";

function minimalIssue(overrides: Partial<Issue> = {}): Issue {
  return {
    date: "2026-01-31",
    title: "Sift — 2026-01-31",
    intro: "Sift scans developer conversations and tech news, then distills real, repeated problems into evidence-backed signals.",
    themes_line: "Today's themes: X, Y.",
    section_title: "## Startup-Grade Idea Cards",
    cards: [
      {
        title: "**Exploitable** Security Flaws",
        hook: "AI code generators create *easily* exploited vulnerabilities.",
        problem: "AI-generated code often contains `predictable` flaws.",
        evidence: ["\"quote\" — Post: https://example.com — Comment: (none)"],
        who_pays: "Security Engineers/Managers",
        stakes: ["Estimate: engineer-hours and MTTR risk."],
        why_now: ["Increased reliance on AI code generation."],
        wedge: { icp: "Start with security teams.", mvp: "A tool that scans AI-generated code." },
        confidence: "low",
      },
    ],
    one_bet: "Enterprises will implement **stricter** guardrails.",
    rejects: ["**catalyst** index 1: not_buildable", "**pain** index 2: news_only"],
    ...overrides,
  };
}

describe("renderIssueEmailHtml", () => {
  it("output contains no raw markdown tokens (##, **, or raw `)", () => {
    const issue = minimalIssue();
    const html = renderIssueEmailHtml(issue);
    expect(html).not.toContain("##");
    expect(html).not.toContain("**");
    // Raw backtick: we convert `...` to <code>...</code>, so no standalone ` in output
    const withoutCodeTags = html.replace(/<code[^>]*>[\s\S]*?<\/code>/g, "");
    expect(withoutCodeTags).not.toContain("`");
  });

  it("section title is stripped of leading ##", () => {
    const issue = minimalIssue({ section_title: "## Startup-Grade Idea Cards" });
    const html = renderIssueEmailHtml(issue);
    expect(html).toContain("Startup-Grade Idea Cards");
    expect(html).not.toContain("## Startup-Grade");
  });

  it("rejects list items render bold as <strong> not **", () => {
    const issue = minimalIssue();
    const html = renderIssueEmailHtml(issue);
    expect(html).toContain("<strong>catalyst</strong>");
    expect(html).toContain("<strong>pain</strong>");
  });
});
