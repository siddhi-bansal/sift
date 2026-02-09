/**
 * Production HTML email template — Sift digest.
 *
 * README (safe to edit / structure):
 * ---------------------------------
 * - SAFE TO EDIT: Brand tokens (BG_DARK, PRIMARY, ACCENT, etc.), "Sift" label text,
 *   footer copy, preheader text logic, and the optional viewInBrowserUrl /
 *   unsubscribeUrl placeholders. Do not remove inline styles from critical
 *   elements (tables, td, a, buttons); email clients rely on them.
 *
 * - INLINE vs <style>:
 *   All critical styling (colors, padding, font, borders, widths) is INLINE on
 *   table/td/a/span so Gmail, Outlook, Apple Mail render correctly. Core text
 *   uses solid hex (no RGBA) to reduce auto-invert artifacts. The <style>
 *   block contains: (1) resets and responsive rules at 620px, (2)
 *   @media (prefers-color-scheme: light) to flip bands/cards to white and
 *   text to #111827/#374151, (3) @media (prefers-color-scheme: dark) to
 *   reinforce the default dark theme, (4) [data-ogsc] selectors for
 *   Outlook.com dark-mode fallbacks. bgcolor attributes on wrapper/header/
 *   bands/cards/footer provide Outlook desktop fallbacks.
 *
 * - KNOWN CLIENT LIMITATIONS:
 *   Gmail may strip or move <style>; Outlook (Windows) uses Word engine and
 *   ignores many CSS properties (border-radius, box-shadow). Buttons are
 *   table-based (bulletproof) for maximum compatibility. No external fonts;
 *   system stack only. Default design = dark theme (charcoal #16181d, cards #23262e); clients that support prefers-color-scheme get light/dark
 *   overrides; others get the inline default.
 */

import type { Issue, StartupGradeCard, WedgeBlock } from "./types";
import {
  stripLeadingHashes,
  markdownInlineToHtml,
  escapeHtml,
} from "./sanitizeMarkdown";

// ---- Brand tokens (match website globals.css) ----
const BG_DARK = "#16181d";
const CARD_BG_DARK = "#23262e";
const BORDER_DARK = "#3b3f47";
const PRIMARY = "#8b5cf6";
const PRIMARY_DIM = "#7c3aed";
const ACCENT = "#f59e0b";
const ACCENT_DIM = "#d97706";
const TEXT_DARK = "#f0f0f0";
const TEXT_SOFT_DARK = "#b8bcc4";
const MUTED_DARK = "#8b9199";
const WARN_BG_DARK = "#2d3139";
const WARN_TEXT_DARK = "#b8bcc4";
// Light mode
const BG_LIGHT = "#f8fafc";
const CARD_BG_LIGHT = "#ffffff";
const BORDER_LIGHT = "#e2e8f0";
const TEXT_LIGHT = "#0f172a";
const BODY_LIGHT = "#475569";
const MUTED_LIGHT = "#94a3b8";

const FONT =
  "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
const PADDING = "24px";
const CELL_BASE = `vertical-align: top; font-family: ${FONT};`;
const CARD_RADIUS = "12px";

function block(tag: string, style: string, content: string): string {
  return `<${tag} style="${style}">${content}</${tag}>`;
}

/** Parse "Today's themes: X, Y, Z." into 2–4 pill labels (no markdown in pills). */
function parseThemes(themesLine: string | undefined): string[] {
  if (!themesLine || !themesLine.trim()) return [];
  const normalized = themesLine.replace(/^Today'?s themes:\s*/i, "").trim();
  const rest = normalized.replace(/\.\s*$/, "").trim();
  const list = rest.split(/[,;]/).map((s) => s.trim()).filter(Boolean);
  return list.slice(0, 4);
}

function renderWedge(w: WedgeBlock): string {
  const parts: string[] = [];
  const liStyle = `margin: 3px 0; font-size: 13px; line-height: 1.4; color: ${TEXT_SOFT_DARK};`;
  const cellStyle = `${CELL_BASE} padding: 0; ${liStyle}`;
  if (w.icp)
    parts.push(
      `<tr><td style="${cellStyle}"><strong>ICP:</strong> ${markdownInlineToHtml(w.icp)}</td></tr>`
    );
  if (w.mvp)
    parts.push(
      `<tr><td style="${cellStyle}"><strong>MVP:</strong> ${markdownInlineToHtml(w.mvp)}</td></tr>`
    );
  if (w.why_they_pay)
    parts.push(
      `<tr><td style="${cellStyle}"><strong>Why they pay:</strong> ${markdownInlineToHtml(w.why_they_pay)}</td></tr>`
    );
  if (w.first_channel)
    parts.push(
      `<tr><td style="${cellStyle}"><strong>First channel:</strong> ${markdownInlineToHtml(w.first_channel)}</td></tr>`
    );
  if (w.anti_feature)
    parts.push(
      `<tr><td style="${cellStyle}"><strong>Anti-feature:</strong> ${markdownInlineToHtml(w.anti_feature)}</td></tr>`
    );
  if (parts.length === 0) return "";
  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 6px;"><tbody>${parts.join("")}</tbody></table>`;
}

/**
 * Bulletproof CTA button: table-based, works in Gmail/Outlook/Apple Mail.
 * href and label are escaped by caller.
 */
function bulletproofButton(href: string, label: string): string {
  return `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="left" style="margin-top: 16px;">
  <tr>
    <td align="center" style="border-radius: 8px; background-color: ${PRIMARY};">
      <a href="${escapeHtml(href)}" target="_blank" style="display: inline-block; padding: 12px 22px; font-family: ${FONT}; font-size: 14px; font-weight: 600; color: #ffffff; text-decoration: none;">${escapeHtml(label)}</a>
    </td>
  </tr>
</table>`;
}

/** Compact field row: small label + value for scannability */
function fieldRow(label: string, value: string, bodyColor: string): string {
  return `<tr><td style="${CELL_BASE} padding: 0;"><table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 10px;"><tr><td style="${CELL_BASE} padding: 0 0 2px 0; font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: ${PRIMARY};">${escapeHtml(label)}</td></tr><tr><td style="${CELL_BASE} padding: 0; font-size: 14px; line-height: 1.45; color: ${bodyColor};">${markdownInlineToHtml(value)}</td></tr></table></td></tr>`;
}

/** Renders one idea card with card-like styling: left accent, scannable layout. */
function renderCard(
  card: StartupGradeCard,
  cardIndex: number,
  viewInBrowserUrl: string
): string {
  const cellStyle = `${CELL_BASE} padding: 0;`;
  const rows: string[] = [];

  // Top row: status pill (if present) + draft badge
  const badges: string[] = [];
  if (card.is_draft) {
    badges.push(`<span class="email-pill-accent" style="display: inline-block; padding: 4px 10px; font-size: 11px; font-weight: 600; color: ${ACCENT_DIM}; background-color: #3d3520; border-radius: 6px;">Draft</span>`);
  }
  const statusDisplay = card.status || card.confidence;
  if (statusDisplay) {
    badges.push(`<span class="email-pill" style="display: inline-block; padding: 4px 10px; font-size: 11px; font-weight: 600; color: ${PRIMARY}; background-color: #2d1f4e; border-radius: 6px;">${escapeHtml(statusDisplay)}</span>`);
  }
  if (badges.length > 0) {
    rows.push(`<tr><td style="${cellStyle} margin-bottom: 12px;">${badges.join(" &nbsp; ")}</td></tr>`);
  }

  // Title: prominent, card-like
  rows.push(
    `<tr><td style="${cellStyle} margin: 0 0 8px 0; font-size: 18px; font-weight: 700; line-height: 1.3; color: ${TEXT_DARK}; letter-spacing: -0.02em;">${markdownInlineToHtml(card.title)}</td></tr>`
  );
  // Hook: one-line summary
  if (card.hook) {
    rows.push(
      `<tr><td style="${cellStyle} margin: 0 0 16px 0; font-size: 15px; line-height: 1.5; color: ${TEXT_SOFT_DARK};">${markdownInlineToHtml(card.hook)}</td></tr>`
    );
  }

  // Key fields in compact scannable format (Problem, Who pays, Why tools fail)
  if (card.problem) {
    rows.push(fieldRow("Problem", card.problem, TEXT_SOFT_DARK));
  }
  if (card.who_pays) {
    rows.push(fieldRow("Who pays", card.who_pays, TEXT_SOFT_DARK));
  }
  if (card.why_existing_tools_fail) {
    rows.push(fieldRow("Why existing tools fail", card.why_existing_tools_fail, TEXT_SOFT_DARK));
  }
  const wedgeCould = card.wedge_could_look_like || card.wedge?.mvp;
  if (wedgeCould) {
    rows.push(fieldRow("What a wedge could look like", wedgeCould, TEXT_SOFT_DARK));
  }

  // Evidence: compact bullets
  if (card.evidence.length > 0) {
    const liStyle = `margin: 2px 0; font-size: 13px; line-height: 1.4; color: ${TEXT_SOFT_DARK};`;
    const bullets = card.evidence
      .map((e) => `<li style="${liStyle}">${markdownInlineToHtml(e)}</li>`)
      .join("");
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 0 0 4px 0; font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: ${PRIMARY};">Evidence</p><ul style="margin: 0 0 12px 0; padding-left: 18px;">${bullets}</ul></td></tr>`
    );
  }

  // Stakes + Why now: compact
  if (card.stakes.length > 0) {
    const compact = card.stakes.map((s) => markdownInlineToHtml(s)).join(" · ");
    rows.push(fieldRow("Stakes", compact, TEXT_SOFT_DARK));
  }
  if (card.why_now.length > 0) {
    const compact = card.why_now.map((w) => markdownInlineToHtml(w)).join(" · ");
    rows.push(fieldRow("Why now", compact, TEXT_SOFT_DARK));
  }

  const statusText = card.status_line
    ? `${card.status || ""}. ${card.status_line}`
    : card.status || card.confidence;
  if (statusText) {
    rows.push(fieldRow("Status", statusText, TEXT_SOFT_DARK));
  }
  if (card.kill_criteria) {
    rows.push(fieldRow("Kill criteria", card.kill_criteria, TEXT_SOFT_DARK));
  }

  const ctaHref = viewInBrowserUrl + (viewInBrowserUrl.indexOf("?") >= 0 ? "&" : "?") + "card=" + cardIndex;
  rows.push(`<tr><td style="${cellStyle} padding-top: 12px; border-top: 1px solid ${BORDER_DARK};">${bulletproofButton(ctaHref, "Read cluster")}</td></tr>`);

  // Card wrapper: left accent bar (4px purple), border, rounded corners
  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="email-card" style="margin-bottom: 28px; border: 1px solid ${BORDER_DARK}; border-left: 4px solid ${PRIMARY}; border-radius: ${CARD_RADIUS}; background-color: ${CARD_BG_DARK};" bgcolor="${CARD_BG_DARK}"><tr><td style="${CELL_BASE} padding: 20px 24px;"><table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tbody>${rows.join("")}</tbody></table></td></tr></table>`;
}

export interface RenderEmailOptions {
  viewInBrowserUrl?: string;
  unsubscribeUrl?: string;
}

/**
 * Renders the issue as production-ready email HTML.
 * Table-based layout, inline CSS for all critical styling. Same cards/sections/order as preview.
 * All injected content is sanitized (no raw markdown in output).
 * Gmail, Apple Mail, Outlook safe. 600px centered. System fonts only.
 * Dark theme by default; clients that support prefers-color-scheme get a light variant in <style>.
 */
export function renderIssueEmailHtml(
  issue: Issue,
  options: RenderEmailOptions = {}
): string {
  const viewInBrowserUrl = options.viewInBrowserUrl ?? "#";
  const unsubscribeUrl = options.unsubscribeUrl ?? "#";

  const titlePlain = stripLeadingHashes(issue.title ?? "");
  const titleDisplay = titlePlain.replace(/\s*—\s*.+$/, "").trim() || titlePlain;
  const preheader =
    titleDisplay || stripLeadingHashes(issue.themes_line ?? "") || "";
  const preheaderHtml = preheader
    ? `<div style="display: none; max-height: 0; overflow: hidden;">${escapeHtml(preheader)}</div>`
    : "";

  const themes = parseThemes(issue.themes_line);
  const sectionTitlePlain = stripLeadingHashes(issue.section_title ?? "");

  // ---- Header: brand bar (primary violet) ----
  const headerBar = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${PRIMARY};" bgcolor="${PRIMARY}" tpl="header">
  <tr>
    <td style="${CELL_BASE} padding: 18px ${PADDING};">
      <span style="font-size: 18px; font-weight: 700; color: #ffffff; letter-spacing: -0.02em;">Signal, not noise. Build what matters.</span>
    </td>
  </tr>
</table>`;

  // ---- Title (below header); intro optional ----
  const titleDateStyle = `margin: 0 0 4px 0; font-size: 22px; font-weight: 700; line-height: 1.3; color: ${TEXT_DARK};`;
  const titleDateBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${BG_DARK};" bgcolor="${BG_DARK}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: ${PADDING}; color: ${TEXT_SOFT_DARK};">
      ${block("h1", titleDateStyle, escapeHtml(titleDisplay))}
      ${issue.intro ? block("p", `margin: 12px 0 0 0; font-size: 15px; line-height: 1.5; color: ${TEXT_SOFT_DARK};`, markdownInlineToHtml(issue.intro)) : ""}
    </td>
  </tr>
</table>`;

  // ---- Themes: 2–4 pill badges (accent amber, like website) ----
  const pillStyle = `display: inline-block; margin: 0 8px 8px 0; padding: 6px 14px; font-size: 12px; font-weight: 600; letter-spacing: 0.03em; color: #1a1612; background-color: ${ACCENT}; border-radius: 999px;`;
  const themesHtml =
    themes.length > 0
      ? themes
          .map((t) => `<span style="${pillStyle}">${escapeHtml(t)}</span>`)
          .join("")
      : "";
  const themesBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${BG_DARK};" bgcolor="${BG_DARK}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 0 ${PADDING} 22px ${PADDING};">
      ${themesHtml}
    </td>
  </tr>
</table>`;

  // ---- Section title ----
  const sectionTitleBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${BG_DARK};" bgcolor="${BG_DARK}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 0 ${PADDING} 14px ${PADDING};">
      <h2 style="margin: 0; font-size: 17px; font-weight: 700; line-height: 1.3; color: ${TEXT_DARK}; letter-spacing: -0.01em;">${escapeHtml(sectionTitlePlain)}</h2>
    </td>
  </tr>
</table>`;

  // ---- Cards (each with CTA) ----
  const cardsHtml = issue.cards
    .map((card, i) => renderCard(card, i, viewInBrowserUrl))
    .join("");

  const cardsBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${BG_DARK};" bgcolor="${BG_DARK}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 0 ${PADDING} 8px ${PADDING};">
      ${cardsHtml}
    </td>
  </tr>
</table>`;

  // ---- One bet + Rejects ----
  const footerParts: string[] = [];
  if (issue.one_bet) {
    footerParts.push(
      `<p style="margin: 0 0 12px 0; font-size: 15px; line-height: 1.5; color: ${TEXT_SOFT_DARK};"><strong style="color: ${ACCENT};">One bet:</strong> ${markdownInlineToHtml(issue.one_bet)}</p>`
    );
  }
  if (issue.rejects.length > 0) {
    footerParts.push(
      `<h2 style="margin: 16px 0 10px 0; font-size: 16px; font-weight: 700; color: ${TEXT_DARK};">Rejects (buildability gate)</h2>`
    );
    const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${TEXT_SOFT_DARK};`;
    const listItems = issue.rejects
      .map((r) => `<li style="${liStyle}">${markdownInlineToHtml(r)}</li>`)
      .join("");
    footerParts.push(
      `<ul style="margin: 0 0 24px 0; padding-left: 20px;">${listItems}</ul>`
    );
  }

  const extraBlock =
    footerParts.length > 0
      ? `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${BG_DARK};" bgcolor="${BG_DARK}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 16px ${PADDING} 28px ${PADDING}; color: ${TEXT_SOFT_DARK};">
      ${footerParts.join("")}
    </td>
  </tr>
</table>`
      : "";

  // ---- Footer: unsubscribe + view in browser ----
  const footerLinkStyle = `color: ${PRIMARY}; text-decoration: none; font-size: 13px; font-weight: 500;`;
  const footerBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${BG_DARK}; border-top: 1px solid ${BORDER_DARK};" bgcolor="${BG_DARK}" tpl="footer">
  <tr>
    <td style="${CELL_BASE} padding: 20px ${PADDING}; color: ${MUTED_DARK};">
      <a href="${escapeHtml(unsubscribeUrl)}" style="${footerLinkStyle}">Unsubscribe</a>
      <span style="color: ${MUTED_DARK}; font-size: 13px;"> &nbsp;·&nbsp; </span>
      <a href="${escapeHtml(viewInBrowserUrl)}" style="${footerLinkStyle}">View in browser</a>
    </td>
  </tr>
</table>`;

  const bodyContent =
    headerBar +
    titleDateBlock +
    themesBlock +
    sectionTitleBlock +
    cardsBlock +
    extraBlock +
    footerBlock;

  const inner = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" class="email-inner" align="center" style="max-width: 600px; width: 100%; background-color: ${BG_DARK};" bgcolor="${BG_DARK}">
  <tr>
    <td style="${CELL_BASE} padding: 0;">
      ${bodyContent}
    </td>
  </tr>
</table>`;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="color-scheme" content="light dark" />
  <title>${escapeHtml(titleDisplay)}</title>
  <style type="text/css">
    body, table, td { -webkit-text-size-adjust: 100%; }
    .email-wrapper { width: 100%; }
    .email-inner { width: 100%; }
    @media only screen and (max-width: 620px) {
      .email-wrapper { width: 100% !important; max-width: 100% !important; }
      .email-inner { width: 100% !important; max-width: 100% !important; }
      .email-inner td { padding-left: 12px !important; padding-right: 12px !important; }
    }
    /* Light mode: clean, readable */
    @media (prefers-color-scheme: light) {
      .email-body-dark { background-color: ${BG_LIGHT} !important; }
      .email-body-dark .email-wrapper,
      .email-body-dark .email-wrapper td { background-color: ${BG_LIGHT} !important; }
      .email-body-dark .email-inner { background-color: ${BG_LIGHT} !important; }
      .email-body-dark .email-inner table[tpl="header"] { background-color: ${PRIMARY} !important; }
      .email-body-dark .email-inner table[tpl="band"],
      .email-body-dark .email-inner table[tpl="band"] td { background-color: #ffffff !important; color: ${BODY_LIGHT} !important; }
      .email-body-dark .email-inner table[tpl="band"] h1,
      .email-body-dark .email-inner table[tpl="band"] h2 { color: ${TEXT_LIGHT} !important; }
      .email-body-dark .email-inner table[tpl="band"] p,
      .email-body-dark .email-inner table[tpl="band"] li { color: ${BODY_LIGHT} !important; }
      .email-body-dark .email-inner .email-card { background-color: ${CARD_BG_LIGHT} !important; border-color: ${BORDER_LIGHT} !important; border-left-color: ${PRIMARY} !important; }
      .email-body-dark .email-inner .email-card td,
      .email-body-dark .email-inner .email-card p,
      .email-body-dark .email-inner .email-card li { color: ${BODY_LIGHT} !important; }
      .email-body-dark .email-inner .email-card [style*="font-weight: 700"] { color: ${TEXT_LIGHT} !important; }
      .email-body-dark .email-inner .email-card .email-warn { background-color: #fef3c7 !important; color: #92400e !important; border-left-color: ${ACCENT} !important; }
      .email-body-dark .email-inner table[tpl="footer"] { background-color: #ffffff !important; border-top-color: ${BORDER_LIGHT} !important; }
      .email-body-dark .email-inner table[tpl="footer"] td { color: ${MUTED_LIGHT} !important; }
      .email-body-dark .email-inner table[tpl="footer"] a { color: ${PRIMARY} !important; }
      .email-body-dark .email-inner table[tpl="footer"] span { color: ${MUTED_LIGHT} !important; }
      .email-body-dark .email-inner .email-card .email-pill { background-color: #ede9fe !important; color: ${PRIMARY_DIM} !important; }
      .email-body-dark .email-inner .email-card .email-pill-accent { background-color: #fef3c7 !important; color: ${ACCENT_DIM} !important; }
    }
    /* Dark mode: website charcoal (default) */
    @media (prefers-color-scheme: dark) {
      .email-body-dark { background-color: ${BG_DARK} !important; }
      .email-body-dark .email-wrapper,
      .email-body-dark .email-wrapper td { background-color: ${BG_DARK} !important; }
      .email-body-dark .email-inner { background-color: ${BG_DARK} !important; }
      .email-body-dark .email-inner table[tpl="band"],
      .email-body-dark .email-inner table[tpl="band"] td { background-color: ${BG_DARK} !important; color: ${TEXT_SOFT_DARK} !important; }
      .email-body-dark .email-inner table[tpl="band"] h1,
      .email-body-dark .email-inner table[tpl="band"] h2 { color: ${TEXT_DARK} !important; }
      .email-body-dark .email-inner .email-card { background-color: ${CARD_BG_DARK} !important; border-color: ${BORDER_DARK} !important; border-left-color: ${PRIMARY} !important; }
      .email-body-dark .email-inner table[tpl="footer"] { background-color: ${BG_DARK} !important; }
      .email-body-dark .email-inner table[tpl="footer"] td,
      .email-body-dark .email-inner table[tpl="footer"] a { color: ${MUTED_DARK} !important; }
    }
    /* Outlook.com dark: [data-ogsc] = dark mode active */
    [data-ogsc] .email-body-dark,
    [data-ogsc] .email-wrapper,
    [data-ogsc] .email-wrapper td { background-color: ${BG_DARK} !important; }
    [data-ogsc] .email-inner { background-color: ${BG_DARK} !important; }
    [data-ogsc] .email-inner table[tpl="band"],
    [data-ogsc] .email-inner table[tpl="band"] td { background-color: ${BG_DARK} !important; color: ${TEXT_SOFT_DARK} !important; }
    [data-ogsc] .email-inner table[tpl="band"] h1,
    [data-ogsc] .email-inner table[tpl="band"] h2 { color: ${TEXT_DARK} !important; }
    [data-ogsc] .email-inner .email-card { background-color: ${CARD_BG_DARK} !important; }
    [data-ogsc] .email-inner table[tpl="footer"] { background-color: ${BG_DARK} !important; }
    [data-ogsc] .email-inner table[tpl="footer"] td,
    [data-ogsc] .email-inner table[tpl="footer"] a { color: ${MUTED_DARK} !important; }
  </style>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <![endif]-->
</head>
<body class="email-body-dark" style="margin: 0; padding: 0; background-color: ${BG_DARK}; font-family: ${FONT}; -webkit-text-size-adjust: 100%;">
${preheaderHtml}
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="email-wrapper" style="background-color: ${BG_DARK};" bgcolor="${BG_DARK}">
  <tr>
    <td align="center" style="padding: 24px 16px;" bgcolor="${BG_DARK}">
      ${inner}
    </td>
  </tr>
</table>
</body>
</html>`;
}
