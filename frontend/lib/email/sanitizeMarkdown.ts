/**
 * Markdown-to-email-HTML sanitizer.
 * Converts inline markdown (** * ` [](url)) to safe HTML; strips leading # for headings.
 * Does NOT generate <h1>-<h6>; headings are controlled by the renderer.
 */

// Unlikely in user content; used so we can escape string then restore tags
const B = "\u0001B\u0002";
const BE = "\u0001/B\u0002";
const E = "\u0001E\u0002";
const EE = "\u0001/E\u0002";
const C = "\u0001C\u0002";
const CE = "\u0001/C\u0002";
const L = "\u0001L\u0002";
const LU = "\u0001U\u0002";
const LE = "\u0001/L\u0002";

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Strip leading #, ##, ### etc. and trim. Use for section/heading text only;
 * do not generate <h1>-<h6> from content.
 */
export function stripLeadingHashes(s: string): string {
  return (s ?? "").replace(/^#+\s*/, "").trim();
}

/**
 * Convert inline markdown to email-safe HTML fragment.
 * **text** -> <strong>text</strong>, *text* -> <em>text</em>,
 * `code` -> <code>code</code>, [text](url) -> <a href="url">text</a>.
 * Escapes remaining HTML. Does not produce <h1>-<h6>.
 */
export function markdownInlineToHtml(s: string): string {
  if (typeof s !== "string" || s.length === 0) return "";
  let out = s;

  // Links first (so [ and ] inside other constructs don't break). Use raw content; escapeHtml(out) will escape it once.
  out = out.replace(/\[([^\]]*)\]\(([^)]*)\)/g, (_m, text: string, url: string) => {
    return L + text.trim() + LU + url.trim() + LE;
  });
  // Bold **...** (before single * so ** is consumed)
  out = out.replace(/\*\*([\s\S]*?)\*\*/g, (_m, c: string) => {
    return B + c.trim() + BE;
  });
  // Italic *...* (single * not part of **)
  out = out.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, (_m, c: string) => {
    return E + c.trim() + EE;
  });
  // Inline code `...`
  out = out.replace(/`([^`]*)`/g, (_m, c: string) => {
    return C + c.trim() + CE;
  });
  // Escape entire string once (placeholder content gets escaped; B/BE etc are control chars so unchanged)
  out = escapeHtml(out);
  // Restore placeholders as tags. For links, $2 is HTML-escaped url; use as href (safe). Escaped " is &quot; which is valid in attr.
  out = out.replace(new RegExp(B + "([\\s\\S]*?)" + BE, "g"), "<strong>$1</strong>");
  out = out.replace(new RegExp(E + "([\\s\\S]*?)" + EE, "g"), "<em>$1</em>");
  out = out.replace(new RegExp(C + "([\\s\\S]*?)" + CE, "g"), "<code style=\"font-size:13px;background:#f0f0f0;padding:1px 4px;\">$1</code>");
  out = out.replace(
    new RegExp(L + "([\\s\\S]*?)" + LU + "([\\s\\S]*?)" + LE, "g"),
    '<a href="$2" style="color:#555;text-decoration:underline;">$1</a>'
  );
  return out;
}

/**
 * Plain text only: strip leading hashes and convert inline markdown to text
 * (no tags). Then escape HTML. Use when you want heading-like text as plain.
 */
export function markdownToPlainHtml(s: string): string {
  return escapeHtml(stripLeadingHashes(s ?? ""));
}

export { escapeHtml, escapeAttr };
