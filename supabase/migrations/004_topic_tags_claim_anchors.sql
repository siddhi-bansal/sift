-- Topic tags and claim anchors for evidence-topic coherence (item_labels)
ALTER TABLE item_labels
  ADD COLUMN IF NOT EXISTS topic_tags JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS claim_anchors JSONB DEFAULT '[]';
