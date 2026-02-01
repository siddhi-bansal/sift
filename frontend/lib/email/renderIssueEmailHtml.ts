/**
 * Production HTML email template — Sift digest.
 *
 * README (safe to edit / structure):
 * ---------------------------------
 * - SAFE TO EDIT: Brand tokens (NAVY, PURPLE, YELLOW, etc.), "Sift" label text,
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
 *   system stack only. Default design = dark theme (navy #0B1020, dark cards
 *   #111827); clients that support prefers-color-scheme get light/dark
 *   overrides; others get the inline default.
 */

import type { Issue, StartupGradeCard, WedgeBlock } from "./types";
import {
  stripLeadingHashes,
  markdownInlineToHtml,
  escapeHtml,
} from "./sanitizeMarkdown";

// ---- Brand tokens (default = dark theme; solid hex to avoid invert artifacts) ----
const NAVY = "#0B1020";
const PURPLE = "#7C3AED";
const YELLOW = "#FBBF24";
const BAND_TITLE = "#F9FAFB";
const BAND_BODY = "#CBD5E1";
const CARD_BG_DARK = "#111827";
const CARD_BORDER_DARK = "rgba(255,255,255,0.12)";
const CARD_TITLE = "#F9FAFB";
const CARD_BODY = "#CBD5E1";
const CARD_LABEL = "#E5E7EB";
const WARN_BG_DARK = "#1F2937";
const WARN_TEXT_DARK = "#CBD5E1";
const FOOTER_TEXT = "#CBD5E1";
const FOOTER_BORDER = "#374151";
const TEXT_LIGHT = "#111827";
const BODY_LIGHT = "#374151";
const BORDER_LIGHT = "#e5e7eb";
const CARD_BG_LIGHT = "#ffffff";

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
  const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${CARD_BODY};`;
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

/** Renders one idea card; default = dark (bg #111827, solid hex text). */
function renderCard(
  card: StartupGradeCard,
  cardIndex: number,
  viewInBrowserUrl: string
): string {
  const cellStyle = `${CELL_BASE} padding: 0;`;
  const rows: string[] = [];

  if (card.is_draft) {
    rows.push(
      `<tr><td style="${cellStyle} font-size: 13px; color: ${CARD_BODY};"><em>Draft — needs more receipts</em></td></tr>`
    );
  }
  rows.push(
    `<tr><td style="${cellStyle} margin: 0 0 6px 0; font-size: 16px; font-weight: 700; line-height: 1.3; color: ${CARD_TITLE};">${markdownInlineToHtml(card.title)}</td></tr>`
  );
  if (card.hook) {
    rows.push(
      `<tr><td style="${cellStyle} margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${CARD_BODY};">${markdownInlineToHtml(card.hook)}</td></tr>`
    );
  }
  if (card.problem) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Problem:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${CARD_BODY};">${markdownInlineToHtml(card.problem)}</p></td></tr>`
    );
  }
  if (card.evidence.length > 0) {
    const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${CARD_BODY};`;
    const bullets = card.evidence
      .map((e) => `<li style="${liStyle}">${markdownInlineToHtml(e)}</li>`)
      .join("");
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Evidence:</p><ul style="margin: 0 0 10px 0; padding-left: 20px;">${bullets}</ul></td></tr>`
    );
  }
  if (card.who_pays) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Who pays:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${CARD_BODY};">${markdownInlineToHtml(card.who_pays)}</p></td></tr>`
    );
  }
  if (card.why_existing_tools_fail) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Why existing tools fail:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${CARD_BODY};">${markdownInlineToHtml(card.why_existing_tools_fail)}</p></td></tr>`
    );
  }
  if (card.stakes.length > 0) {
    const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${CARD_BODY};`;
    const bullets = card.stakes
      .map((s) => `<li style="${liStyle}">${markdownInlineToHtml(s)}</li>`)
      .join("");
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Stakes:</p><ul style="margin: 0 0 10px 0; padding-left: 20px;">${bullets}</ul></td></tr>`
    );
  }
  if (card.why_now.length > 0) {
    const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${CARD_BODY};`;
    const bullets = card.why_now
      .map((w) => `<li style="${liStyle}">${markdownInlineToHtml(w)}</li>`)
      .join("");
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Why now:</p><ul style="margin: 0 0 10px 0; padding-left: 20px;">${bullets}</ul></td></tr>`
    );
  }
  const wedgeHtml = renderWedge(card.wedge);
  if (wedgeHtml) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Wedge:</p>${wedgeHtml}</td></tr>`
    );
  }
  if (card.confidence) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Confidence:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${CARD_BODY};">${markdownInlineToHtml(card.confidence)}</p></td></tr>`
    );
  }
  if (card.kill_criteria) {
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Kill criteria:</p><p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${CARD_BODY};">${markdownInlineToHtml(card.kill_criteria)}</p></td></tr>`
    );
  }
  if (card.warnings && card.warnings.length > 0) {
    const warnText = markdownInlineToHtml(card.warnings.join("; "));
    const warnBox = `margin: 8px 0 0 0; padding: 10px 12px; font-size: 12px; line-height: 1.4; color: ${WARN_TEXT_DARK}; background-color: ${WARN_BG_DARK}; border-radius: 4px;`;
    rows.push(
      `<tr><td style="${cellStyle}"><p style="margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: ${CARD_LABEL};">Warnings:</p><div class="email-warn" style="${warnBox}">${warnText}</div></td></tr>`
    );
  }

  const ctaHref = viewInBrowserUrl + (viewInBrowserUrl.indexOf("?") >= 0 ? "&" : "?") + "card=" + cardIndex;
  const ctaHtml = bulletproofButton(ctaHref, "Read cluster");

  rows.push(
    `<tr><td style="${cellStyle} padding-top: 8px;">${ctaHtml}</td></tr>`
  );

  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="email-card" style="margin-bottom: 24px; border: 1px solid ${CARD_BORDER_DARK}; border-radius: 8px; background-color: ${CARD_BG_DARK};" bgcolor="${CARD_BG_DARK}"><tr><td style="${CELL_BASE} padding: 16px 20px;"><table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tbody>${rows.join("")}</tbody></table></td></tr></table>`;
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

  // ---- Header: purple brand bar (bgcolor for Outlook) ----
  const headerBar = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${PURPLE};" bgcolor="${PURPLE}" tpl="header">
  <tr>
    <td style="${CELL_BASE} padding: 14px ${PADDING};">
      <span style="font-size: 18px; font-weight: 700; color: #000000; letter-spacing: -0.02em;">Signal, not noise. Build what matters.</span>
    </td>
  </tr>
</table>`;

  // ---- Title (below header, no date); intro optional ----
  const titleDateStyle = `margin: 0 0 4px 0; font-size: 22px; font-weight: 700; line-height: 1.3; color: ${BAND_TITLE};`;
  const titleDateBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" bgcolor="${NAVY}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: ${PADDING}; color: ${BAND_BODY};">
      ${block("h1", titleDateStyle, escapeHtml(titleDisplay))}
      ${issue.intro ? block("p", `margin: 12px 0 0 0; font-size: 15px; line-height: 1.5; color: ${BAND_BODY};`, markdownInlineToHtml(issue.intro)) : ""}
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
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" bgcolor="${NAVY}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 0 ${PADDING} 20px ${PADDING};">
      ${themesHtml}
    </td>
  </tr>
</table>`;

  // ---- Section title ----
  const sectionTitleBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" bgcolor="${NAVY}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 0 ${PADDING} 12px ${PADDING};">
      <h2 style="margin: 0; font-size: 18px; font-weight: 700; line-height: 1.3; color: ${BAND_TITLE};">${escapeHtml(sectionTitlePlain)}</h2>
    </td>
  </tr>
</table>`;

  // ---- Cards (each with CTA); default = dark cards #111827 ----
  const cardsHtml = issue.cards
    .map((card, i) => renderCard(card, i, viewInBrowserUrl))
    .join("");

  const cardsBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" bgcolor="${NAVY}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 0 ${PADDING};">
      ${cardsHtml}
    </td>
  </tr>
</table>`;

  // ---- One bet + Rejects (solid hex text) ----
  const footerParts: string[] = [];
  if (issue.one_bet) {
    footerParts.push(
      `<p style="margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: ${BAND_BODY};"><strong>One bet:</strong> ${markdownInlineToHtml(issue.one_bet)}</p>`
    );
  }
  if (issue.rejects.length > 0) {
    footerParts.push(
      `<h2 style="margin: 16px 0 8px 0; font-size: 18px; font-weight: 700; color: ${BAND_TITLE};">Rejects (buildability gate)</h2>`
    );
    const liStyle = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: ${BAND_BODY};`;
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
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY};" bgcolor="${NAVY}" tpl="band">
  <tr>
    <td style="${CELL_BASE} padding: 12px ${PADDING} 24px ${PADDING}; color: ${BAND_BODY};">
      ${footerParts.join("")}
    </td>
  </tr>
</table>`
      : "";

  // ---- Footer: unsubscribe + view in browser (solid hex) ----
  const footerLinkStyle = `color: ${FOOTER_TEXT}; text-decoration: underline; font-size: 13px;`;
  const footerBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background-color: ${NAVY}; border-top: 1px solid ${FOOTER_BORDER};" bgcolor="${NAVY}" tpl="footer">
  <tr>
    <td style="${CELL_BASE} padding: 20px ${PADDING}; color: ${FOOTER_TEXT};">
      <a href="${escapeHtml(unsubscribeUrl)}" style="${footerLinkStyle}">Unsubscribe</a>
      <span style="color: ${FOOTER_TEXT}; font-size: 13px;"> &nbsp;·&nbsp; </span>
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
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" class="email-inner" align="center" style="max-width: 600px; width: 100%; background-color: ${NAVY};" bgcolor="${NAVY}">
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
    /* Light mode: bands and cards white, text dark */
    @media (prefers-color-scheme: light) {
      .email-body-dark { background-color: #f5f5f5 !important; }
      .email-body-dark .email-wrapper,
      .email-body-dark .email-wrapper td { background-color: #f5f5f5 !important; }
      .email-body-dark .email-inner { background-color: #f5f5f5 !important; }
      .email-body-dark .email-inner table[tpl="header"] { background-color: ${PURPLE} !important; }
      .email-body-dark .email-inner table[tpl="band"],
      .email-body-dark .email-inner table[tpl="band"] td { background-color: #ffffff !important; color: ${TEXT_LIGHT} !important; }
      .email-body-dark .email-inner table[tpl="band"] h1,
      .email-body-dark .email-inner table[tpl="band"] h2 { color: ${TEXT_LIGHT} !important; }
      .email-body-dark .email-inner table[tpl="band"] p,
      .email-body-dark .email-inner table[tpl="band"] li { color: ${BODY_LIGHT} !important; }
      .email-body-dark .email-inner .email-card { background-color: ${CARD_BG_LIGHT} !important; border-color: ${BORDER_LIGHT} !important; }
      .email-body-dark .email-inner .email-card td,
      .email-body-dark .email-inner .email-card p,
      .email-body-dark .email-inner .email-card li { color: ${BODY_LIGHT} !important; }
      .email-body-dark .email-inner .email-card h3,
      .email-body-dark .email-inner .email-card [style*="font-weight: 700"] { color: ${TEXT_LIGHT} !important; }
      .email-body-dark .email-inner .email-card [style*="font-weight: 600"] { color: ${BODY_LIGHT} !important; }
      .email-body-dark .email-inner .email-card .email-warn { background-color: #f3f4f6 !important; color: ${BODY_LIGHT} !important; }
      .email-body-dark .email-inner table[tpl="footer"] { background-color: #ffffff !important; border-top-color: ${BORDER_LIGHT} !important; }
      .email-body-dark .email-inner table[tpl="footer"] td,
      .email-body-dark .email-inner table[tpl="footer"] a { color: ${PURPLE} !important; }
      .email-body-dark .email-inner table[tpl="footer"] span { color: ${BODY_LIGHT} !important; }
    }
    /* Dark mode: reinforce navy/card dark (default) */
    @media (prefers-color-scheme: dark) {
      .email-body-dark { background-color: ${NAVY} !important; }
      .email-body-dark .email-wrapper,
      .email-body-dark .email-wrapper td { background-color: ${NAVY} !important; }
      .email-body-dark .email-inner { background-color: ${NAVY} !important; }
      .email-body-dark .email-inner table[tpl="band"],
      .email-body-dark .email-inner table[tpl="band"] td { background-color: ${NAVY} !important; color: ${BAND_BODY} !important; }
      .email-body-dark .email-inner table[tpl="band"] h1,
      .email-body-dark .email-inner table[tpl="band"] h2 { color: ${BAND_TITLE} !important; }
      .email-body-dark .email-inner .email-card { background-color: ${CARD_BG_DARK} !important; border-color: ${CARD_BORDER_DARK} !important; }
      .email-body-dark .email-inner table[tpl="footer"] { background-color: ${NAVY} !important; }
      .email-body-dark .email-inner table[tpl="footer"] td,
      .email-body-dark .email-inner table[tpl="footer"] a { color: ${FOOTER_TEXT} !important; }
    }
    /* Outlook.com dark: [data-ogsc] = dark mode active */
    [data-ogsc] .email-body-dark,
    [data-ogsc] .email-wrapper,
    [data-ogsc] .email-wrapper td { background-color: ${NAVY} !important; }
    [data-ogsc] .email-inner { background-color: ${NAVY} !important; }
    [data-ogsc] .email-inner table[tpl="band"],
    [data-ogsc] .email-inner table[tpl="band"] td { background-color: ${NAVY} !important; color: ${BAND_BODY} !important; }
    [data-ogsc] .email-inner table[tpl="band"] h1,
    [data-ogsc] .email-inner table[tpl="band"] h2 { color: ${BAND_TITLE} !important; }
    [data-ogsc] .email-inner .email-card { background-color: ${CARD_BG_DARK} !important; }
    [data-ogsc] .email-inner table[tpl="footer"] { background-color: ${NAVY} !important; }
    [data-ogsc] .email-inner table[tpl="footer"] td,
    [data-ogsc] .email-inner table[tpl="footer"] a { color: ${FOOTER_TEXT} !important; }
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
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="email-wrapper" style="background-color: ${NAVY};" bgcolor="${NAVY}">
  <tr>
    <td align="center" style="padding: 24px 16px;" bgcolor="${NAVY}">
      ${inner}
    </td>
  </tr>
</table>
</body>
</html>`;
}
