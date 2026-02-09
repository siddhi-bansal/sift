/**
 * Parse stored report markdown (format from newsletter_style.format_startup_grade_card)
 * into Issue JSON. Single source of truth: the same markdown shown in the preview.
 */

import type { Issue, StartupGradeCard, WedgeBlock } from "./types";

const INTRO_PREFIX = "Sift scans";
const INTRO_PREFIX_LEGACY = "Unmet scans";
const THEMES_PREFIX = "Today's themes:";
const SECTION_STARTUP = "## Startup-Grade Idea Cards";
const SECTION_DRAFT = "## Draft / Needs more receipts";
const CARD_HEADING = /^### \*\*(.+?)\*\*$/;
const BOLD_LABEL = /^\*\*(.+?):\*\*\s*(.*)$/;
const BULLET = /^-\s+(.+)$/;
const HORIZON = /^---$/;
const REJECTS_HEADING = "## Rejects (buildability gate)";
const ONE_BET_PREFIX = "One bet:";

function trim(s: string): string {
  return (s ?? "").trim();
}

function parseCardBlock(lines: string[]): StartupGradeCard | null {
  if (lines.length === 0) return null;
  const titleMatch = lines[0].match(CARD_HEADING);
  if (!titleMatch) return null;
  const title = titleMatch[1].trim();
  const hookLines: string[] = [];
  let problem = "";
  const evidence: string[] = [];
  let who_pays = "";
  let why_existing_tools_fail = "";
  let wedge_could_look_like = "";
  const stakes: string[] = [];
  const why_now: string[] = [];
  const wedge: WedgeBlock = {};
  let status = "";
  let status_line = "";
  let kill_criteria = "";
  let is_draft = false;

  let i = 1;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed) {
      i++;
      continue;
    }
    if (CARD_HEADING.test(trimmed)) break;
    if (trimmed === "---") break;

    if (trimmed.startsWith("*(Draft") && trimmed.includes("receipts)*")) {
      is_draft = true;
      i++;
      continue;
    }

    const boldMatch = trimmed.match(BOLD_LABEL);
    if (boldMatch) {
      const [, label, value] = boldMatch;
      const key = label.trim().toLowerCase();
      const val = (value ?? "").trim();
      if (key === "problem") problem = val;
      else if (key === "who pays") who_pays = val;
      else if (key === "why existing tools fail") why_existing_tools_fail = val;
      else if (key === "what a wedge could look like") wedge_could_look_like = val;
      else if (key === "status") {
        // Format: "Early signal — recurring but thin evidence. Only one HN thread so far."
        const periodIdx = val.indexOf(". ");
        if (periodIdx >= 0) {
          status = val.slice(0, periodIdx).trim();
          status_line = val.slice(periodIdx + 2).trim();
        } else {
          status = val;
        }
      }       else if (key === "kill criteria") kill_criteria = val;
      else if (key === "who is affected" || key === "confidence" || key === "warnings") {
        /* Legacy fields — ignore */
      }
      i++;
      continue;
    }

    if (trimmed === "**Evidence:**") {
      i++;
      while (i < lines.length && lines[i].trim().startsWith("- ")) {
        evidence.push(lines[i].trim().replace(/^-\s+/, "").trim());
        i++;
      }
      continue;
    }
    if (trimmed === "**Stakes:**") {
      i++;
      while (i < lines.length && lines[i].trim().startsWith("- ")) {
        stakes.push(lines[i].trim().replace(/^-\s+/, "").trim());
        i++;
      }
      continue;
    }
    if (trimmed === "**Why now:**") {
      i++;
      while (i < lines.length && lines[i].trim().startsWith("- ")) {
        why_now.push(lines[i].trim().replace(/^-\s+/, "").trim());
        i++;
      }
      continue;
    }
    if (trimmed === "**Wedge:**") {
      i++;
      while (i < lines.length) {
        const ln = lines[i].trim();
        if (!ln.startsWith("- ")) break;
        const rest = ln.replace(/^-?\s*/, "");
        if (rest.startsWith("ICP:")) wedge.icp = rest.replace(/^ICP:\s*/i, "").trim();
        else if (rest.startsWith("MVP:")) wedge.mvp = rest.replace(/^MVP:\s*/i, "").trim();
        else if (rest.toLowerCase().startsWith("why they pay:")) wedge.why_they_pay = rest.replace(/^Why they pay:\s*/i, "").trim();
        else if (rest.toLowerCase().startsWith("first channel:")) wedge.first_channel = rest.replace(/^First channel:\s*/i, "").trim();
        else if (rest.toLowerCase().startsWith("anti-feature:")) wedge.anti_feature = rest.replace(/^Anti-feature:\s*/i, "").trim();
        i++;
      }
      continue;
    }

    if (!problem && !trimmed.startsWith("**")) {
      hookLines.push(trimmed);
    }
    i++;
  }

  const hook = hookLines.join(" ").trim();

  return {
    title,
    hook: hook.trim(),
    problem,
    evidence,
    who_pays,
    why_existing_tools_fail: why_existing_tools_fail || undefined,
    wedge_could_look_like: wedge_could_look_like || undefined,
    stakes,
    why_now,
    wedge,
    status: status || undefined,
    status_line: status_line || undefined,
    kill_criteria: kill_criteria || undefined,
    is_draft: is_draft || undefined,
  };
}

export function parseIssueFromMarkdown(markdown: string): Issue | null {
  const lines = markdown.split(/\r?\n/);
  let date = "";
  let title = "";
  let intro = "";
  let themes_line = "";
  let section_title = SECTION_STARTUP;
  const cards: StartupGradeCard[] = [];
  let one_bet = "";
  const rejects: string[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const t = line.trim();
    if (line.startsWith("# Sift — ")) {
      date = line.replace("# Sift — ", "").trim();
      title = `Sift — ${date}`;
      i++;
      continue;
    }
    if (line.startsWith("# Unmet — ")) {
      date = line.replace("# Unmet — ", "").trim();
      title = `Sift — ${date}`;
      i++;
      continue;
    }
    if (intro === "" && (t.includes(INTRO_PREFIX) || t.includes(INTRO_PREFIX_LEGACY))) {
      intro = t;
      i++;
      continue;
    }
    if (t.startsWith(THEMES_PREFIX)) {
      themes_line = t;
      i++;
      continue;
    }
    if (line.trim() === SECTION_STARTUP || line.trim() === SECTION_DRAFT) {
      section_title = line.trim();
      i++;
      continue;
    }
    if (line.trim().startsWith(REJECTS_HEADING)) {
      i++;
      while (i < lines.length) {
        const ln = lines[i].trim();
        if (ln.startsWith("- ")) rejects.push(ln.replace(/^-\s+/, "").trim());
        i++;
      }
      break;
    }
    if (t.startsWith(ONE_BET_PREFIX)) {
      one_bet = t.replace(ONE_BET_PREFIX, "").trim();
      i++;
      continue;
    }

    const cardMatch = line.match(CARD_HEADING);
    if (cardMatch) {
      const cardLines: string[] = [line];
      i++;
      while (i < lines.length && !lines[i].trim().match(CARD_HEADING) && lines[i].trim() !== "---") {
        cardLines.push(lines[i]);
        i++;
      }
      const card = parseCardBlock(cardLines);
      if (card) cards.push(card);
      continue;
    }
    i++;
  }

  if (!date) return null;
  return {
    date,
    title,
    intro,
    themes_line,
    section_title,
    cards,
    one_bet,
    rejects,
  };
}
