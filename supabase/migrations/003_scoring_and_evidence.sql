-- Scoring and evidence: extend item_labels and raw_items for classify_and_score + evidence_snippets

-- item_labels: add audience_fit, pain_intensity, actionability, evidence_spans, exclude_reason
ALTER TABLE item_labels
  ADD COLUMN IF NOT EXISTS audience_fit NUMERIC(4,3) CHECK (audience_fit >= 0 AND audience_fit <= 1),
  ADD COLUMN IF NOT EXISTS pain_intensity NUMERIC(4,3) CHECK (pain_intensity >= 0 AND pain_intensity <= 1),
  ADD COLUMN IF NOT EXISTS actionability NUMERIC(4,3) CHECK (actionability >= 0 AND actionability <= 1),
  ADD COLUMN IF NOT EXISTS evidence_spans JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS exclude_reason TEXT;

-- raw_items: evidence_snippets (2-4 short pain-language snippets from item + comments)
ALTER TABLE raw_items
  ADD COLUMN IF NOT EXISTS evidence_snippets JSONB DEFAULT '[]';

-- catalyst_items: new schema fields (what_changed, who_feels_it, problems_created array, opportunity_wedge, confidence)
ALTER TABLE catalyst_items
  ADD COLUMN IF NOT EXISTS what_changed TEXT,
  ADD COLUMN IF NOT EXISTS who_feels_it TEXT,
  ADD COLUMN IF NOT EXISTS opportunity_wedge TEXT,
  ADD COLUMN IF NOT EXISTS confidence NUMERIC(4,3) CHECK (confidence >= 0 AND confidence <= 1);
