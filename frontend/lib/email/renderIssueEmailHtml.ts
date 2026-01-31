/**
 * Render Issue as production-ready email HTML.
 * Table-based layout, inline CSS only. Same cards/sections/order as preview.
 * All injected content is sanitized: no raw markdown (##, **, `) in output.
 * Gmail, Apple Mail, Outlook safe. 600px centered. System fonts only.
 */

import type { Issue, StartupGradeCard, WedgeBlock } from "./types";
import {
  stripLeadingHashes,
  markdownInlineToHtml,
  escapeHtml,
} from "./sanitizeMarkdown";

const FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

// Single main padding; reduce repeated left/right
const PADDING = "24px";
const CELL_BASE = `vertical-align: top; font-family: ${FONT};`;

// Type scale: title 22px, section 16–18px, body 14–15px
const H1_STYLE = `margin: 0 0 12px 0; font-size: 22px; font-weight: 700; line-height: 1.3; color: #1a1a1a;`;
const H2_STYLE = `margin: 0 0 8px 0; font-size: 18px; font-weight: 700; line-height: 1.3; color: #1a1a1a;`;
const H3_STYLE = `margin: 0 0 6px 0; font-size: 16px; font-weight: 700; line-height: 1.3; color: #1a1a1a;`;
const P_STYLE = `margin: 0 0 10px 0; font-size: 15px; line-height: 1.5; color: #1a1a1a;`;
const LABEL_STYLE = `margin: 10px 0 4px 0; font-size: 14px; font-weight: 600; color: #333;`;
const LI_STYLE = `margin: 4px 0; font-size: 14px; line-height: 1.45; color: #333;`;
const MUTED_STYLE = `font-size: 13px; color: #555;`;
// Warnings: light background, smaller text
const WARNINGS_BOX = `margin: 8px 0 0 0; padding: 10px 12px; font-size: 12px; line-height: 1.4; color: #555; background: #f5f5f5; border-radius: 4px;`;

function block(tag: string, style: string, content: string): string {
  return `<${tag} style="${style}">${content}</${tag}>`;
}

function renderWedge(w: WedgeBlock): string {
  const parts: string[] = [];
  const cellStyle = `${CELL_BASE} padding: 0; ${LI_STYLE}`;
  if (w.icp) parts.push(`<tr><td style="${cellStyle}"><strong>ICP:</strong> ${markdownInlineToHtml(w.icp)}</td></tr>`);
  if (w.mvp) parts.push(`<tr><td style="${cellStyle}"><strong>MVP:</strong> ${markdownInlineToHtml(w.mvp)}</td></tr>`);
  if (w.why_they_pay) parts.push(`<tr><td style="${cellStyle}"><strong>Why they pay:</strong> ${markdownInlineToHtml(w.why_they_pay)}</td></tr>`);
  if (w.first_channel) parts.push(`<tr><td style="${cellStyle}"><strong>First channel:</strong> ${markdownInlineToHtml(w.first_channel)}</td></tr>`);
  if (w.anti_feature) parts.push(`<tr><td style="${cellStyle}"><strong>Anti-feature:</strong> ${markdownInlineToHtml(w.anti_feature)}</td></tr>`);
  if (parts.length === 0) return "";
  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-top: 6px;"><tbody>${parts.join("")}</tbody></table>`;
}

function renderCard(card: StartupGradeCard): string {
  const cellStyle = `${CELL_BASE} padding: 0 0 12px 0;`;
  const rows: string[] = [];

  if (card.is_draft) {
    rows.push(`<tr><td style="${cellStyle} ${MUTED_STYLE}"><em>Draft — needs more receipts</em></td></tr>`);
  }
  rows.push(`<tr><td style="${cellStyle}">${block("h3", H3_STYLE, markdownInlineToHtml(card.title))}</td></tr>`);
  if (card.hook) {
    rows.push(`<tr><td style="${cellStyle}">${block("p", P_STYLE, markdownInlineToHtml(card.hook))}</td></tr>`);
  }
  if (card.problem) {
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Problem:</p><p style="${P_STYLE}">${markdownInlineToHtml(card.problem)}</p></td></tr>`);
  }
  if (card.evidence.length > 0) {
    const bullets = card.evidence.map((e) => `<li style="${LI_STYLE}">${markdownInlineToHtml(e)}</li>`).join("");
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Evidence:</p><ul style="margin: 0 0 10px 0; padding-left: 20px;">${bullets}</ul></td></tr>`);
  }
  if (card.who_pays) {
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Who pays:</p><p style="${P_STYLE}">${markdownInlineToHtml(card.who_pays)}</p></td></tr>`);
  }
  if (card.why_existing_tools_fail) {
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Why existing tools fail:</p><p style="${P_STYLE}">${markdownInlineToHtml(card.why_existing_tools_fail)}</p></td></tr>`);
  }
  if (card.stakes.length > 0) {
    const bullets = card.stakes.map((s) => `<li style="${LI_STYLE}">${markdownInlineToHtml(s)}</li>`).join("");
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Stakes:</p><ul style="margin: 0 0 10px 0; padding-left: 20px;">${bullets}</ul></td></tr>`);
  }
  if (card.why_now.length > 0) {
    const bullets = card.why_now.map((w) => `<li style="${LI_STYLE}">${markdownInlineToHtml(w)}</li>`).join("");
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Why now:</p><ul style="margin: 0 0 10px 0; padding-left: 20px;">${bullets}</ul></td></tr>`);
  }
  const wedgeHtml = renderWedge(card.wedge);
  if (wedgeHtml) {
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Wedge:</p>${wedgeHtml}</td></tr>`);
  }
  if (card.confidence) {
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Confidence:</p><p style="${P_STYLE}">${markdownInlineToHtml(card.confidence)}</p></td></tr>`);
  }
  if (card.kill_criteria) {
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Kill criteria:</p><p style="${P_STYLE}">${markdownInlineToHtml(card.kill_criteria)}</p></td></tr>`);
  }
  if (card.warnings && card.warnings.length > 0) {
    const warnText = markdownInlineToHtml(card.warnings.join("; "));
    rows.push(`<tr><td style="${cellStyle}"><p style="${LABEL_STYLE}">Warnings:</p><div style="${WARNINGS_BOX}">${warnText}</div></td></tr>`);
  }

  // Card container: light border + radius (table wrapper for Outlook)
  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="margin-bottom: 24px; border: 1px solid #e5e5e5; border-radius: 8px; background: #ffffff;"><tr><td style="${CELL_BASE} padding: 16px 20px;"><table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tbody>${rows.join("")}</tbody></table></td></tr></table>`;
}

/**
 * Returns full email HTML: same cards/sections/order as the issue preview.
 * No raw markdown tokens (##, **, `) in output. Self-contained, inline CSS only.
 */
export function renderIssueEmailHtml(issue: Issue): string {
  const titlePlain = stripLeadingHashes(issue.title ?? "");
  const preheader = titlePlain || stripLeadingHashes(issue.themes_line ?? "") || "";
  const preheaderHtml = preheader
    ? `<div style="display: none; max-height: 0; overflow: hidden;">${escapeHtml(preheader)}</div>`
    : "";

  const sections: string[] = [];

  // Top header block: subtle background, border bottom, padding
  const headerBlock = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background: #fafafa; border-bottom: 1px solid #eee;">
  <tr>
    <td style="${CELL_BASE} padding: ${PADDING};">
      ${block("h1", H1_STYLE, escapeHtml(titlePlain))}
      ${issue.intro ? block("p", P_STYLE, markdownInlineToHtml(issue.intro)) : ""}
      ${issue.themes_line ? block("p", P_STYLE, markdownInlineToHtml(issue.themes_line)) : ""}
    </td>
  </tr>
</table>`;
  sections.push(headerBlock);

  // Section title: strip ## so "## Startup-Grade Idea Cards" -> "Startup-Grade Idea Cards"
  const sectionTitlePlain = stripLeadingHashes(issue.section_title ?? "");
  sections.push(`<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tr><td style="${CELL_BASE} padding: ${PADDING} 24px 12px 24px;">${block("h2", H2_STYLE, escapeHtml(sectionTitlePlain))}</td></tr></table>`);

  for (const card of issue.cards) {
    sections.push(`<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tr><td style="${CELL_BASE} padding: 0 ${PADDING};">${renderCard(card)}</td></tr></table>`);
  }

  // One bet + Rejects in main padding container
  const footerParts: string[] = [];
  if (issue.one_bet) {
    footerParts.push(`<p style="${P_STYLE} margin-top: 8px;"><strong>One bet:</strong> ${markdownInlineToHtml(issue.one_bet)}</p>`);
  }
  if (issue.rejects.length > 0) {
    footerParts.push(block("h2", H2_STYLE, "Rejects (buildability gate)"));
    const listItems = issue.rejects.map((r) => `<li style="${LI_STYLE}">${markdownInlineToHtml(r)}</li>`).join("");
    footerParts.push(`<ul style="margin: 0 0 24px 0; padding-left: 20px;">${listItems}</ul>`);
  }
  if (footerParts.length > 0) {
    sections.push(`<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"><tr><td style="${CELL_BASE} padding: 12px ${PADDING} 24px;">${footerParts.join("")}</td></tr></table>`);
  }

  const bodyContent = sections.join("");
  const inner = `
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600" class="email-inner" align="center" style="max-width: 600px; width: 100%; background: #ffffff;">
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
  <title>${escapeHtml(titlePlain)}</title>
  <style type="text/css">
    @media only screen and (max-width: 620px) {
      .email-wrapper { width: 100% !important; max-width: 100% !important; }
      .email-inner { width: 100% !important; max-width: 100% !important; }
      .email-inner td { padding-left: 12px !important; padding-right: 12px !important; }
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
<body style="margin: 0; padding: 0; background: #f5f5f5; font-family: ${FONT}; -webkit-text-size-adjust: 100%;">
${preheaderHtml}
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="email-wrapper" style="background: #f5f5f5;">
  <tr>
    <td align="center" style="padding: 24px 16px;">
      ${inner}
    </td>
  </tr>
</table>
</body>
</html>`;
}
