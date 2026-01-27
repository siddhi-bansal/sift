## TODO

- Per-user interest curation
- Simplify wording for skimming

CURSOR PROMPT FOR SIMPLIFYING WORDING FOR SKIMMING:
You are my senior fullstack engineer. Update the newsletter generator so the output is (a) skimmable, (b) simple/clear English, (c) meaningfully different from generic link-digest newsletters, and (d) non-hallucinatory: it must only claim what is supported by the ingested evidence.

Current issues:
- Reads like a neutral report (bland, interchangeable with TLDR/Half Baked).
- Vague/corporate phrases (“This showcases…”, “This highlights…”, “raises questions…”).
- Not enough POV / builder lens.
- Not very skimmable.
- No pattern language tying the day together.
- “Possible wedge” ideas sometimes feel ungrounded.

PRIMARY CONSTRAINT: NO HALLUCINATIONS
- Every factual claim must be traceable to the underlying items (title/text/snippet/comments/metadata).
- If something isn’t directly supported, do NOT assert it. Instead use guarded language:
  - “Seems like…”, “One plausible read…”, “Could indicate…”
- Never invent tool names, company names, numbers, quotes, timelines, or causal claims.
- Include evidence anchors per cluster/catalyst:
  - Use a short “Evidence:” line with 1–3 short snippets (<= 12 words each) pulled verbatim from source text OR titles, plus links.
  - If verbatim snippets aren’t available, use only titles + links and keep language cautious.

Goal style:
Tone: smart friend / builder newsletter. Light opinion + direction, not hot takes.
Voice: punchy, specific, plain English. Short sentences.
Skimmable: bold hook line + bullets + consistent structure.

Implement these changes end-to-end:

1) Add a short intro at the top (2–3 lines max)
- Explain what Unmet is and that claims are evidence-based.

2) Enforce a strict template for EVERY item (pain cluster, rising, catalyst, wildcard)

For each item output:
A) **Bold hook sentence** (1 line, 8–14 words; no “This article…”)
B) 1–2 sentence explanation (simple language; no buzzwords; evidence-grounded)
C) Why this is interesting (2–3 bullets; concrete; no fluff)
D) Who feels this (one short line; persona)
E) Possible wedge (one short line; must be plausible and grounded)
F) Evidence (1–3 ultra-short verbatim snippets OR titles; plus max 3 links)

Hard caps:
- Each item <= 120 words excluding links.
- Max links per item: 3.

3) Add section-level “pattern language”
- After the intro, add 1–2 lines like:
  - “Today clusters around: ____”
- Only state patterns supported by today’s clusters/catalysts.

4) Improve section layout (and keep it short)
- Top Pain Clusters (max 5)
- Rising Pain Signals (max 3; else “No clear risers today.”)
- Catalyst Signals (max 5)
- Wildcard (1)

5) Add light scoring/texture (derived from data; no guesswork)
- Pain clusters: “Signal strength: Low/Med/High” from cluster size + avg pain_score + model confidence.
- Catalysts: “Impact: Low/Med/High” from interest-match count + source credibility heuristic + urgency keywords (keep heuristic transparent).

6) Remove corporate/vague phrasing
- Add a banned phrase list and ensure generator avoids them:
  - “This highlights”, “This showcases”, “This contributes”, “raises questions about”
  - “Existing tools are often”, “need for robust”, “increased competition”
- Replace with direct language:
  - “Teams are doing X because…”, “The bottleneck is…”, “This creates an opening for…”

7) Implement as a formatting + rewriting layer (not just “prompt better”)
- Create `newsletter_style.py` (or similar) that:
  - Defines schema for a newsletter item
  - Validates fields and word limits
  - Enforces banned phrases
  - Enforces evidence grounding (requires evidence snippets + links)
- Add a `rewrite_into_template(draft, item_type, evidence_bundle)` step:
  - Use Gemini to produce STRICT JSON with fields:
    hook, explanation, why_bullets[], who, wedge, evidence_snippets[], links[], strength_or_impact
  - Strictly validate JSON; if invalid, retry with a repair prompt.
  - If still invalid, fallback to deterministic template using existing text (no new claims).

8) “One line I’d bet on” (final line at very end)
- Exactly ONE sentence.
- Choose the most buildable wedge of the day.
- Must be grounded in evidence (don’t invent).
- Implementation:
  - Compute buildability score:
    - Pain clusters: signal strength + persona clarity + wedge specificity (all derived)
    - Catalysts: impact + directness of new buyer pain
  - If all low, phrase cautiously: “Worth exploring: …”

9) Make it testable + fast to iterate
- Add fixtures (sample clusters + sample news items + sample raw evidence).
- Add `python -m unmet render_sample` to output a sample newsletter in the new style.
- Update README describing the new format + grounding rules.

Deliverables:
- Update backend modules as needed.
- Ensure the newsletter output is visibly more readable, skimmable, and has light POV while staying evidence-based.
- Keep deterministic-ish formatting and consistent structure day to day.
