/**
 * Issue and card types matching the backend report structure.
 * Same schema and ordering as format_startup_grade_card in newsletter_style.py.
 */

export interface WedgeBlock {
  icp?: string;
  mvp?: string;
  why_they_pay?: string;
  first_channel?: string;
  anti_feature?: string;
}

export interface StartupGradeCard {
  title: string;
  hook: string;
  problem: string;
  evidence: string[];
  who_pays: string;
  why_existing_tools_fail?: string;
  wedge_could_look_like?: string;
  stakes: string[];
  why_now: string[];
  wedge: WedgeBlock;
  status?: string; // External: "Early signal" | "Moderate signal" | "Strong signal"
  status_line?: string; // Short explanatory line
  confidence?: string; // Internal; prefer status for display
  kill_criteria?: string;
  is_draft?: boolean;
}

export interface Issue {
  date: string;
  title: string;
  intro: string;
  themes_line: string;
  section_title: string;
  cards: StartupGradeCard[];
  one_bet: string;
  rejects: string[];
}
