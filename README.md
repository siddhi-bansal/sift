# Unmet — Pain & Catalyst Newsletter

Daily digest of **pain signals** (complaints, unmet needs, workflows people hate) and **catalyst signals** (industry news that creates urgency or new problems). We ingest from Hacker News, Reddit, and RSS; cluster and summarize with Gemini; and produce a markdown newsletter.

## Product concept

- **Sources:** HN (Firebase API), Reddit (PRAW, subreddits from subscriber interests), RSS (feeds from interests).
- **Pain signals:** Heuristic + Gemini classification (PAIN / DISCUSSION / NEWS / OTHER), then clustering (embeddings or TF-IDF). Cluster summarization and “rising” vs previous day.
- **Catalyst signals:** From news items (RSS), 3–7 bullets with “what problems it may create.”
- **Output:** Top Pain Clusters, Rising Pain Signals, Catalyst Signals, Wildcard. Stored in `daily_reports` and written to `/out/YYYY-MM-DD.md`.

Interests, subreddits, and RSS feeds are **stored in Supabase** and seeded via a script — no hardcoding in app logic.

---

## Repo layout

```
unmet/
├── backend/          # Python 3.11 pipeline + CLI
│   ├── unmet/        # Package: ingest, analyze, run, db, gemini_client, seed_data
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
     `cd backend && pip install -e . && python -m unmet seed`
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
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` — from [Reddit app](https://www.reddit.com/prefs/apps) (optional; omit to skip Reddit)

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
python -m unmet ingest --date 2026-01-26
```

**Analyze** (pain score, Gemini labels, clustering → `item_labels`, `clusters`, `cluster_items`):

```bash
python -m unmet analyze --date 2026-01-26
```

**Run** (summarize clusters, catalyst bullets, build report → `daily_reports`, `catalyst_items`, `/out/YYYY-MM-DD.md`):

```bash
python -m unmet run --date 2026-01-26
```

**Full pipeline for “today”:**

```bash
export TODAY=$(date +%Y-%m-%d)
python -m unmet ingest --date $TODAY
python -m unmet analyze --date $TODAY
python -m unmet run --date $TODAY
```

Then open `/preview?date=$TODAY` or read `out/$TODAY.md`.

**Seed** (interests + interest_sources):

```bash
python -m unmet seed
```

---

## 5. Generate today’s newsletter and preview it

1. Set env (backend and frontend as above).
2. Apply migrations and seed (Supabase + `python -m unmet seed`).
3. Run pipeline for today:
   ```bash
   cd backend
   python -m unmet ingest --date $(date +%Y-%m-%d)
   python -m unmet analyze --date $(date +%Y-%m-%d)
   python -m unmet run --date $(date +%Y-%m-%d)
   ```
4. Start frontend and open `/preview?date=<today>`.
5. Or open `out/<today>.md` in the repo.

---

## 6. Running daily (cron / GitHub Actions)

**Cron** (run at a fixed time every day, e.g. 6:00 UTC):

```cron
0 6 * * * cd /path/to/unmet/backend && . .venv/bin/activate && export $(grep -v '^#' .env | xargs) && python -m unmet ingest --date $(date +\%Y-\%m-\%d) && python -m unmet analyze --date $(date +\%Y-\%m-\%d) && python -m unmet run --date $(date +\%Y-\%m-\%d)
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
          REDDIT_USER_AGENT: UnmetNewsletter/1.0
        run: |
          TODAY=$(date +%Y-%m-%d)
          cd backend && python -m unmet ingest --date $TODAY
          cd backend && python -m unmet analyze --date $TODAY
          cd backend && python -m unmet run --date $TODAY
```

Add the same env vars as repo **Secrets**. Adjust paths if your workflow runs from repo root.

---

## Logging, retries, rate limits

- **Logging:** Python pipeline uses `logging`; level and format are set in `unmet/cli.py`.
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
