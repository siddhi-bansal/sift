# Sift — Signal, not noise. Build what matters.

Daily digest of **pain signals** (complaints, unfulfilled needs, workflows people hate) and **catalyst signals** (industry news that creates urgency or new problems). We ingest from Hacker News, Reddit, and RSS; cluster and summarize with Gemini; and produce a markdown newsletter.

## Pipeline overview

**Ingest** pulls posts from HN, Reddit, and RSS (sources from Supabase) and writes them to `raw_items`. **Analyze** scores and labels each item (PAIN / DISCUSSION / NEWS / OTHER), keeps PAIN/DISCUSSION, embeds (or TF-IDF) and clusters them, then writes `clusters` and `cluster_items`. **Run** summarizes each cluster and news items with Gemini, computes rising clusters vs the previous day and picks a wildcard, then rewrites every item into the strict newsletter template (evidence-grounded, no hallucinations). The final markdown is written to `daily_reports` and `/out/YYYY-MM-DD.md`.

## Product concept

- **Sources:** HN (Firebase API), Reddit (Apify scrapers or PRAW; subreddits from subscriber interests), RSS (feeds from interests).
- **Pain signals:** Heuristic + Gemini classification (PAIN / DISCUSSION / NEWS / OTHER), then clustering (embeddings or TF-IDF). Cluster summarization and “rising” vs previous day.
- **Catalyst signals:** From news items (RSS), 3–7 bullets with “what problems it may create.”
- **Output:** Top Pain Clusters (max 5), Rising Pain Signals (max 3), Catalyst Signals (max 5), Wildcard (1). Stored in `daily_reports` and written to `/out/YYYY-MM-DD.md`. Each item follows a strict template: bold hook, explanation, bullets, who, wedge, evidence snippets + links. See **Newsletter format & grounding** below.

Interests, subreddits, and RSS feeds are **stored in Supabase** and seeded via a script — no hardcoding in app logic.

### Newsletter format & grounding

Newsletter output is **skimmable**, **plain English**, **builder lens**, and **non-hallucinatory**:

- **Intro:** 2–3 lines explaining what Sift is and that every claim is tied to evidence.
- **Pattern language:** A short “Today clusters around: …” line derived from today’s cluster and catalyst themes.
- **Per-item template (pain cluster, rising, catalyst, wildcard):**
  - **Bold hook** (8–14 words, no “This article…”)
  - 1–2 sentence explanation (evidence-grounded)
  - 2–3 “why this is interesting” bullets
  - **Who** (persona) and **Possible wedge** (plausible, grounded)
  - **Evidence:** 1–3 ultra-short verbatim snippets (≤12 words each) or titles, plus up to 3 links
  - **Signal strength** (pain/rising/wildcard) or **Impact** (catalysts): Low/Med/High from cluster size, pain/confidence, or catalyst interest/urgency
- **One line I’d bet on:** One sentence at the end—the most buildable wedge of the day, or “Worth exploring: …” when signals are weak.

**Grounding rules (no hallucinations):**

- Every factual claim must be traceable to underlying items (title/text/snippet/comments).
- Never invent tool names, company names, numbers, quotes, timelines, or causal claims.
- Use guarded language when unsure: “Seems like…”, “One plausible read…”, “Could indicate…”
- Banned phrases (e.g. “This highlights”, “This showcases”, “raises questions about”) are enforced; we use direct language instead.

To preview the format without running the full pipeline:  
`python -m sift render_sample` — outputs a sample newsletter from fixtures in the new style (no API calls).

### Scoring, Editor Gate, and Fallbacks

- **Scope config:** `backend/sift/config.py` defines `NEWSLETTER_AUDIENCE` (B2B builders/devtools founders), `INCLUDED_TOPICS` (devtools, infra, security, data, AI ops, cloud, compliance, SaaS ops, observability, developer productivity, payments infra, platform engineering), and `EXCLUDED_TOPICS` (local human interest, agriculture/food giveaways, sports, celebrity, lifestyle, pure politics unless directly impacts tech compliance/operations). All ranking and selection functions reference this scope.
- **Scoring:** Each raw item is classified and scored with one Gemini call (`classify_and_score_item`): label (PAIN/DISCUSSION/NEWS/OTHER), confidence, audience_fit, pain_intensity, actionability, evidence_spans (verbatim ≤12-word snippets), exclude_reason. We then compute **Sift score** = 0.35×audience_fit + 0.30×pain_intensity + 0.25×actionability + 0.10×confidence − noise_penalty. Noise penalties apply for "Show HN" non-PAIN, generic RSS with no pain evidence, and when exclude_reason is set. Only items with label in {PAIN, DISCUSSION}, audience_fit ≥ 0.65, (pain_intensity ≥ 0.50 or actionability ≥ 0.60), and confidence ≥ 0.55 pass the **candidate filter**. We keep the top N=50 by score (configurable via `EDITOR_GATE_TOP_N`).
- **Editor Gate:** One Gemini call per day selects which candidates make it into the newsletter: **featured_pain_ids**, **secondary_pain_ids**, **catalyst_ids**, and **rejects** (with reason: off-scope, weak evidence, not actionable, duplicate). Only items in featured + secondary pain ids are clustered and summarized; catalysts are gated separately. Rejects are logged (e.g. "Reject id=… reason=off-scope").
- **Catalyst gating:** Catalysts must fit B2B/devtools; excluded topics (e.g. food giveaways, sports) are not included unless they directly impact tech compliance/operations. Each catalyst has a narrow buyer and specific problems; opportunity_wedge follows "Start with &lt;buyer&gt; who &lt;situation&gt;, build &lt;first feature&gt;" or "Unclear from evidence." We allow 0 catalysts if none pass.
- **Editorial fallbacks:** If after filtering and editor gate there are &lt;2 good pain clusters, we publish **1 deep pain** (first cluster) plus **Watchlist themes** (2 short bullets from other clusters/themes) and skip the full "Rising" section. If no catalysts pass gating, we show **"No catalysts worth your attention today."** If clustering yields &lt;2 clusters, we skip the "Rising" section entirely (no "No clear risers today" boilerplate). We prefer shipping fewer, higher-quality items over filler.
- **Evidence:** HN items get top comments fetched and stored in metadata (with post_id, comment_id, author, created_at, text, and derived permalinks: post_url, comment_url); pain candidates get 2–4 **evidence_snippets** (pain-language extraction) saved to `raw_items.evidence_snippets`. Summaries and idea-card prompts use structured **evidence_bullets** (quote + post link + comment link); every claim must be supported by evidence; when evidence is thin or post-only we output "Unclear from evidence" and auto-lower confidence.
- **Embedding resilience:** Embedding runs in a subprocess (`python -m sift.embed_worker input.json output.json`) so a segfault does not crash the main run. On failure we retry with smaller batch sizes (50 → 16 → 4). If embedding still fails, we fall back to TF-IDF for clustering and log clearly.

---

## Repo layout

```
sift/                  # Sift repo
├── backend/          # Python 3.11 pipeline + CLI
│   ├── sift/         # Package: ingest, analyze, run, db, gemini_client, newsletter_style, fixtures
│   └── pyproject.toml
├── frontend/         # Next.js 14 (App Router) landing + signup + preview
├── supabase/
│   ├── migrations/   # 001_schema.sql, 002_rls.sql
│   └── seed.sql      # Optional SQL seed (or use backend seed)
├── out/              # Generated newsletters (YYYY-MM-DD.md)
├── .env.example
└── README.md
```

---

## 1. Supabase setup

1. Create a project at [supabase.com](https://supabase.com).
2. In **Settings → API**: copy **Project URL**, **anon/public** key, **service_role** key.
3. In **Settings → Database**: copy the **Connection string** (URI) for “Direct connection” or “Transaction pooler” — this is `SUPABASE_DB_URL`. Use the format that includes the password.

4. Run the schema and RLS:
   - Either via Supabase Dashboard **SQL Editor**: paste and run `supabase/migrations/001_schema.sql`, then `supabase/migrations/002_rls.sql`.
   - Or with [Supabase CLI](https://supabase.com/docs/guides/cli):  
     `supabase db push` (if you’ve linked the project and migrations are in `supabase/migrations/`).

5. Seed interests and sources:
   - **Option A:** Run the backend seed (recommended):  
     `cd backend && pip install -e . && python -m sift seed`
   - **Option B:** In SQL Editor, run `supabase/seed.sql` after the schema.

---

## 2. Env setup

**Backend** (or repo root):

```bash
cp .env.example .env
```

Fill in:

- `SUPABASE_URL` — Project URL
- `SUPABASE_SERVICE_ROLE_KEY` — service_role key (backend only)
- `SUPABASE_DB_URL` — Postgres connection string (preferred for backend)
- `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/apikey)
- **HN ingest (optional):** `HN_POST_LIMIT` (default **25** posts per run), `HN_COMMENTS_PER_POST` (default **30** top comments per post). Fewer posts and more comments per post keep the pipeline comment-heavy for problem-centric idea cards with forensic evidence (post + comment permalinks).
- **Reddit:** use either **Apify** (no Reddit approval) or **PRAW** (official API).  
  - Apify: `APIFY_API_TOKEN` from [Apify Console → Integrations](https://console.apify.com/settings/integrations); optional `APIFY_REDDIT_ACTOR` (default `trudax/reddit-scraper`).  
  - PRAW: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` from [Reddit app](https://www.reddit.com/prefs/apps).  
  If `APIFY_API_TOKEN` is set, Reddit ingest uses Apify; otherwise it uses PRAW when Reddit credentials are present.

**Frontend:**

```bash
cd frontend
cp .env.local.example .env.local
```

Set:

- `NEXT_PUBLIC_SUPABASE_URL` — same Project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — anon/public key

---

## 3. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). You get:

- **Landing:** headline, short explainer, signup form (email + multi-select interests from DB).
- **Submit:** stores in `subscribers` and `subscriber_interests`; shows confirmation.
- **Preview:** [/preview](http://localhost:3000/preview) or `/preview?date=YYYY-MM-DD` shows the daily report markdown from `daily_reports`.

No auth for MVP. Emails are validated; duplicates are handled (e.g. “already subscribed” or upsert + replace interests).

---

## 4. Run backend: ingest → analyze → run

Use a single date (e.g. today) for a full run. All commands support `--date YYYY-MM-DD`.

```bash
cd backend
pip install -e .
```

Ensure `.env` (or `backend/.env`) has `SUPABASE_DB_URL` and `GEMINI_API_KEY`.

**Ingest** (HN + Reddit + RSS → `raw_items`):

```bash
python -m sift ingest --date 2026-01-26
```

**Analyze** (pain score, Gemini labels, clustering → `item_labels`, `clusters`, `cluster_items`):

```bash
python -m sift analyze --date 2026-01-26
```

**Run** (summarize clusters, catalyst bullets, build report → `daily_reports`, `catalyst_items`, `/out/YYYY-MM-DD.md`):

```bash
python -m sift run --date 2026-01-26
```

**Full pipeline for “today”:**

```bash
export TODAY=$(date +%Y-%m-%d)
python -m sift ingest --date $TODAY
python -m sift analyze --date $TODAY
python -m sift run --date $TODAY
```

Then open `/preview?date=$TODAY` or read `out/$TODAY.md`.

**Seed** (interests + interest_sources):

```bash
python -m sift seed
```

**Render sample** (sample newsletter in the new style, no API):

```bash
python -m sift render_sample
```

---

## 5. Generate today’s newsletter and preview it

1. Set env (backend and frontend as above).
2. Apply migrations and seed (Supabase + `python -m sift seed`).
3. Run pipeline for today:
   ```bash
   cd backend
   python -m sift ingest --date $(date +%Y-%m-%d)
   python -m sift analyze --date $(date +%Y-%m-%d)
   python -m sift run --date $(date +%Y-%m-%d)
   ```
4. Start frontend and open `/preview?date=<today>`.
5. Or open `out/<today>.md` in the repo.

---

## 6. Running daily (cron / GitHub Actions)

**Cron** (run at a fixed time every day, e.g. 6:00 UTC):

```cron
0 6 * * * cd /path/to/sift/backend && . .venv/bin/activate && export $(grep -v '^#' .env | xargs) && python -m sift ingest --date $(date +\%Y-\%m-\%d) && python -m sift analyze --date $(date +\%Y-\%m-\%d) && python -m sift run --date $(date +\%Y-\%m-\%d)
```

**GitHub Actions** (example workflow that runs at 6:00 UTC):

Create `.github/workflows/daily-newsletter.yml`:

```yaml
name: Daily newsletter
on:
  schedule:
    - cron: '0 6 * * *'
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install backend
        run: cd backend && pip install -e .
      - name: Ingest
        env:
          SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
          REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
          REDDIT_USER_AGENT: SiftNewsletter/1.0
        run: |
          TODAY=$(date +%Y-%m-%d)
          cd backend && python -m sift ingest --date $TODAY
          cd backend && python -m sift analyze --date $TODAY
          cd backend && python -m sift run --date $TODAY
```

Add the same env vars as repo **Secrets**. For Reddit, use either `APIFY_API_TOKEN` (Apify) or `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` (PRAW). Adjust paths if your workflow runs from repo root.

---

## Testing

**Backend**

- **CLI (no DB/API):** `cd backend && python -m sift render_sample` — should print Sift markdown.
- **Tests without pytest:** `cd backend && python run_tests.py` — runs scoring and newsletter_style checks (no pytest plugin load).
- **Full test suite:** `cd backend && pip install -e ".[dev]" && pytest tests/ -v`  
  If you see `ImportError: get_ref_type from omegaconf` (or similar), your system Python has a conflicting Hydra/omegaconf. Use a clean venv: `python -m venv .venv && source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows), then `pip install -e ".[dev]" && pytest tests/`.

**Frontend**

- `cd frontend && npm test -- --run` — runs email render tests.

---

## Logging, retries, rate limits

- **Logging:** Python pipeline uses `logging`; level and format are set in `backend/sift/cli.py`.
- **Retries:** Gemini `generate_text` uses a small retry loop with backoff on 429 / resource_exhausted.
- **Rate limits:** Ingest uses conservative defaults (e.g. HN/Reddit/RSS limits via env). Gemini embed calls use short sleeps between requests when batching.

---

## Schema (summary)

- **interests** — id, name, description  
- **interest_sources** — interest_id, source_type (`subreddit`|`rss`), source_value, weight  
- **subscribers** — id, email, created_at  
- **subscriber_interests** — subscriber_id, interest_id  
- **raw_items** — source, source_id, url, title, text, author, published_at, fetched_at, metadata  
- **item_labels** — raw_item_id, label, confidence, pain_score  
- **clusters** — date, cluster_index, title, summary, persona, why_matters, size, score, top_terms, example_urls  
- **cluster_items** — cluster_id, raw_item_id  
- **daily_reports** — date, markdown_content, generated_at  
- **catalyst_items** — date, title, summary, interests, problems_created, source_urls  

Details are in `supabase/migrations/001_schema.sql`.
