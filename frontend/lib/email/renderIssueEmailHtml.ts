/**
 * Production HTML email template — Unmet digest.
 *
 * README (safe to edit / structure):
 * ---------------------------------
 * - SAFE TO EDIT: Brand tokens (NAVY, PURPLE, YELLOW, etc.), "Unmet" label text,
 *   footer copy, preheader text logic, and the optional viewInBrowserUrl /
 *   unsubscribeUrl placeholders. Do not remove inline styles from critical
 *   elements (tables, td, a, buttons); email clients rely on them.
 *
 * - INLINE vs <style>:
 *   All critical styling (colors, padding, font, borders, widths) is INLINE on
 *   table/td/a/span so Gmail, Outlook, Apple Mail render correctly. The only
 *   <style> block contains: (1) resets for body/table, (2) responsive
 *   max-width/padding for .email-wrapper and .email-inner at 620px, (3)
 *   prefers-color-scheme: light overrides so clients that support it show a
 *   light-background variant. Clients that ignore <style> get the inline
 *   default (dark navy + light card content), which is the intended fallback.
 *
 * - KNOWN CLIENT LIMITATIONS:
 *   Gmail may strip or move <style>; Outlook (Windows) uses Word engine and
 *   ignores many CSS properties (border-radius, box-shadow). Buttons are
 *   table-based (bulletproof) for maximum compatibility. No external fonts;
 *   system stack only. Dark mode via prefers-color-scheme is supported in
 *   Apple Mail and some others; Gmail/Outlook will show the inline default.
 */

import type { Issue, StartupGradeCard, WedgeBlock } from "./types";
import {
  stripLeadingHashes,
  markdownInlineToHtml,
  escapeHtml,
} from "./sanitizeMarkdown";

// ---- Brand tokens (from site: navy, purple, yellow; safe to change) ----
const NAVY = "#0B1020";
const PURPLE = "#7C3AED";
const YELLOW = "#FBBF24";
const TEXT_DARK = "rgba(255,255,255,0.92)";
const TEXT_SOFT_DARK = "rgba(255,255,255,0.75)";
const TEXT_LIGHT = "#1a1a1a";
const MUTED_LIGHT = "#555";
const CARD_BG_DARK = "#16181d";
const CARD_BG_LIGHT = "#ffffff";
const BORDER_LIGHT = "#e5e7eb";

const FONT =
  "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
const PADDING = "24px";
const CELL_BASE = `vertical-align: top; font-family: ${FONT};`;

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
  const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${MUTED_LIGHT};`;
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
  const textColor = "#ffffff";
  return `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="left" style="margin-top: 12px;">
  <tr>
    <td align="center" style="border-radius: 8px; background-color: ${PURPLE};">
      <a href="${escapeHtml(href)}" target="_blank" style="display: inline-block; padding: 12px 20px; font-family: ${FONT}; font-size: 14px; font-weight: 600; color: ${textColor}; text-decoration: none;">${escapeHtml(label)}</a>
    </td>
  </tr>
</table>`;
}

function renderCard(
  card: StartupGradeCard,
  cardIndex: number,
  viewInBrowserUrl: string,
  darkMode: boolean
): string {
  const isLight = !darkMode;
  const bg = isLight ? CARD_BG_LIGHT : CARD_BG_DARK;
  const titleColor = isLight ? TEXT_LIGHT : TEXT_DARK;
  const bodyColor = isLight ? MUTED_LIGHT : TEXT_SOFT_DARK;
  const labelColor = isLight ? "#374151" : TEXT_SOFT_DARK;
  const borderColor = isLight ? BORDER_LIGHT : "rgba(255,255,255,0.12)";

  const cellStyle = `${CELL_BASE} padding: 0;`;
  const rows: string[] = [];

  if (card.is_draft) {
    rows.push(
      `<tr><td style="${cellStyle} font-size: 13px; color: ${bodyColor};"><em>Draft — needs more receipts</em></td></tr>`
    );
  }
  rows.push(
    `<tr><td style="${cellStyle} margin: 0 0 6px 0; font-size: 16px; font-weight: 700; line-height: 1.3; color: ${titleColor};">${markdownInlineToHtml(card.title)}</td></tr>`
  );
  if (card.hook) {
    rows.push(
      `<tr><td style="${cellStyle} margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${bodyColor};">${markdownInlineToHtml(card.hook)}</td></tr>`
    );
  }
  if (card.problem) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Problem:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${bodyColor};">${markdownInlineToHtml(card.problem)}</p></td></tr>`
    );
  }
  if (card.evidence.length > 0) {
    const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${bodyColor};`;
    const bullets = card.evidence
      .map((e) => `<li style="${liStyle}">${markdownInlineToHtml(e)}</li>`)
      .join("");
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Evidence:</p><ul style="margin: 0 0 10px 0; padding-left: 20px;">${bullets}</ul></td></tr>`
    );
  }
  if (card.who_pays) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Who pays:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${bodyColor};">${markdownInlineToHtml(card.who_pays)}</p></td></tr>`
    );
  }
  if (card.why_existing_tools_fail) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Why existing tools fail:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${bodyColor};">${markdownInlineToHtml(card.why_existing_tools_fail)}</p></td></tr>`
    );
  }
  if (card.stakes.length > 0) {
    const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${bodyColor};`;
    const bullets = card.stakes
      .map((s) => `<li style="${liStyle}">${markdownInlineToHtml(s)}</li>`)
      .join("");
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Stakes:</p><ul style="margin: 0 0 10px 0; padding-left: 20px;">${bullets}</ul></td></tr>`
    );
  }
  if (card.why_now.length > 0) {
    const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${bodyColor};`;
    const bullets = card.why_now
      .map((w) => `<li style="${liStyle}">${markdownInlineToHtml(w)}</li>`)
      .join("");
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Why now:</p><ul style="margin: 0 0 10px 0; padding-left: 20px;">${bullets}</ul></td></tr>`
    );
  }
  const wedgeHtml = renderWedge(card.wedge);
  if (wedgeHtml) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Wedge:</p>${wedgeHtml}</td></tr>`
    );
  }
  if (card.confidence) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Confidence:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${bodyColor};">${markdownInlineToHtml(card.confidence)}</p></td></tr>`
    );
  }
  if (card.kill_criteria) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Kill criteria:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${bodyColor};">${markdownInlineToHtml(card.kill_criteria)}</p></td></tr>`
    );
  }
  if (card.warnings && card.warnings.length > 0) {
    const warnText = markdownInlineToHtml(card.warnings.join("; "));
    const warnBox = `margin: 8px 0 0 0; padding: 10px 12px; font-size: 12px; line-height: 1.4; color: ${bodyColor}; background: rgba(0,0,0,0.06); border-radius: 4px;`;
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${labelColor};">Warnings:</p><div style="${warnBox}">${warnText}</div></td></tr>`
    );
  }

  const ctaHref = viewInBrowserUrl + (viewInBrowserUrl.indexOf("?") >= 0 ? "&" : "?") + "card=" + cardIndex;
  const ctaHtml = bulletproofButton(ctaHref, "Read cluster");

  rows.push(
    `<tr><td style="${cellStyle} padding-top: 8px;">${ctaHtml}</td></tr>`
  );

  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 24px; border: 1px solid ${borderColor}; border-radius: 8px; background: ${bg};"><tr><td style="${CELL_BASE} padding: 16px 20px;"><table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tbody>${rows.join("")}</tbody></table></td></tr></table>`;
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
  const preheader =
    titlePlain || stripLeadingHashes(issue.themes_line ?? "") || "";
  const preheaderHtml = preheader
    ? `<div style="display: none; max-height: 0; overflow: hidden;">${escapeHtml(preheader)}</div>`
    : "";

  const themes = parseThemes(issue.themes_line);
  const sectionTitlePlain = stripLeadingHashes(issue.section_title ?? "");

  // ---- Header: purple brand bar ----
  const headerBar = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${PURPLE};" tpl="header">
  <tr>
    <td style="${CELL_BASE} padding: 14px ${PADDING};">
      <span style="font-size: 18px; font-weight: 700; color: #ffffff; letter-spacing: -0.02em;">Unmet</span>
    </td>
  </tr>
</table>`;

  // ---- Title + date (below header, on navy in default) ----
  const titleDateStyle = `margin: 0 0 4px 0; font-size: 22px; font-weight: 700; line-height: 1.3; color: ${TEXT_DARK};`;
  const dateStyle = `margin: 0; font-size: 14px; color: ${TEXT_SOFT_DARK};`;
  const titleDateBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: ${PADDING};">
      ${block("h1", titleDateStyle, escapeHtml(titlePlain))}
      ${issue.date ? `<p style="${dateStyle}">${escapeHtml(issue.date)}</p>` : ""}
      ${issue.intro ? block("p", `margin: 12px 0 0 0; font-size: 15px; line-height: 1.5; color: ${TEXT_SOFT_DARK};`, markdownInlineToHtml(issue.intro)) : ""}
    </td>
  </tr>
</table>`;

  // ---- Themes: 2–4 pill badges (yellow highlight) ----
  const pillStyle = `display: inline-block; margin: 0 6px 6px 0; padding: 6px 12px; font-size: 13px; font-weight: 600; color: ${NAVY}; background-color: ${YELLOW}; border-radius: 999px;`;
  const themesHtml =
    themes.length > 0
      ? themes
          .map((t) => `<span style="${pillStyle}">${escapeHtml(t)}</span>`)
          .join("")
      : "";
  const themesBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 0 ${PADDING} 20px ${PADDING};">
      ${themesHtml}
    </td>
  </tr>
</table>`;

  // ---- Section title ----
  const sectionTitleBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 0 ${PADDING} 12px ${PADDING};">
      <h2 style="margin: 0; font-size: 18px; font-weight: 700; line-height: 1.3; color: ${TEXT_DARK};">${escapeHtml(sectionTitlePlain)}</h2>
    </td>
  </tr>
</table>`;

  // ---- Cards (each with CTA); card surface is always light for contrast on navy ----
  const cardsHtml = issue.cards
    .map((card, i) => renderCard(card, i, viewInBrowserUrl, false))
    .join("");

  const cardsBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 0 ${PADDING};">
      ${cardsHtml}
    </td>
  </tr>
</table>`;

  // ---- One bet + Rejects ----
  const footerParts: string[] = [];
  if (issue.one_bet) {
    footerParts.push(
      `<p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${TEXT_SOFT_DARK};"><strong>One bet:</strong> ${markdownInlineToHtml(issue.one_bet)}</p>`
    );
  }
  if (issue.rejects.length > 0) {
    footerParts.push(
      `<h2 style="margin: 16px 0 8px 0; font-size: 18px; font-weight: 700; color: ${TEXT_DARK};">Rejects (buildability gate)</h2>`
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
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 12px ${PADDING} 24px ${PADDING};">
      ${footerParts.join("")}
    </td>
  </tr>
</table>`
      : "";

  // ---- Footer: unsubscribe + view in browser ----
  const footerLinkStyle = `color: ${TEXT_SOFT_DARK}; text-decoration: underline; font-size: 13px;`;
  const footerBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY}; border-top: 1px solid rgba(255,255,255,0.1);" tpl="footer">
  <tr>
    <td style="${CELL_BASE} padding: 20px ${PADDING};">
      <a href="${escapeHtml(unsubscribeUrl)}" style="${footerLinkStyle}">Unsubscribe</a>
      <span style="color: ${TEXT_SOFT_DARK}; font-size: 13px;"> &nbsp;·&nbsp; </span>
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
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" class="email-inner" align="center" style="max-width: 600px; width: 100%; background-color: ${NAVY};">
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
  <title>${escapeHtml(titlePlain)}</title>
  <style type="text/css">
    body, table, td { -webkit-text-size-adjust: 100%; }
    .email-wrapper { width: 100%; }
    .email-inner { width: 100%; }
    @media only screen and (max-width: 620px) {
      .email-wrapper { width: 100% !important; max-width: 100% !important; }
      .email-inner { width: 100% !important; max-width: 100% !important; }
      .email-inner td { padding-left: 12px !important; padding-right: 12px !important; }
    }
    @media (prefers-color-scheme: light) {
      .email-body-dark .email-inner { background-color: #f5f5f5 !important; }
      .email-body-dark .email-inner table[tpl="header"] { background-color: ${PURPLE} !important; }
      .email-body-dark .email-inner table[tpl="band"] { background-color: #f5f5f5 !important; }
      .email-body-dark .email-inner table[tpl="band"] td { color: #1a1a1a !important; }
      .email-body-dark .email-inner table[tpl="band"] h1 { color: #1a1a1a !important; }
      .email-body-dark .email-inner table[tpl="band"] p { color: #555 !important; }
      .email-body-dark .email-inner table[tpl="footer"] { background-color: #f5f5f5 !important; border-top-color: #e5e7eb !important; }
      .email-body-dark .email-inner table[tpl="footer"] a { color: #7C3AED !important; }
    }
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
<body class="email-body-dark" style="margin: 0; padding: 0; background-color: ${NAVY}; font-family: ${FONT}; -webkit-text-size-adjust: 100%;">
${preheaderHtml}
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="email-wrapper" style="background-color: ${NAVY};">
  <tr>
    <td align="center" style="padding: 24px 16px;">
      ${inner}
    </td>
  </tr>
</table>
</body>
</html>`;
}
