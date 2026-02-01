-- Sift newsletter schema
-- Run order: 001_schema.sql, then seed via backend script or 002_seed.sql

-- Interests (topics users can subscribe to)
CREATE TABLE IF NOT EXISTS interests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Sources per interest: subreddits or RSS feeds (no hardcoding in app)
CREATE TABLE IF NOT EXISTS interest_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  interest_id UUID NOT NULL REFERENCES interests(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('subreddit', 'rss')),
  source_value TEXT NOT NULL,
  weight NUMERIC(3,2) DEFAULT 1.0 CHECK (weight >= 0 AND weight <= 2),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(interest_id, source_type, source_value)
);

CREATE INDEX idx_interest_sources_interest ON interest_sources(interest_id);
CREATE INDEX idx_interest_sources_type ON interest_sources(source_type);

-- Subscribers
CREATE TABLE IF NOT EXISTS subscribers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Subscriber interest selections
CREATE TABLE IF NOT EXISTS subscriber_interests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscriber_id UUID NOT NULL REFERENCES subscribers(id) ON DELETE CASCADE,
  interest_id UUID NOT NULL REFERENCES interests(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(subscriber_id, interest_id)
);

CREATE INDEX idx_subscriber_interests_sub ON subscriber_interests(subscriber_id);
CREATE INDEX idx_subscriber_interests_interest ON subscriber_interests(interest_id);

-- Raw ingested items (HN, Reddit, RSS)
CREATE TABLE IF NOT EXISTS raw_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  url TEXT,
  title TEXT,
  text TEXT,
  author TEXT,
  published_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ DEFAULT now(),
  metadata JSONB DEFAULT '{}',
  UNIQUE(source, source_id)
);

CREATE INDEX idx_raw_items_source ON raw_items(source);
CREATE INDEX idx_raw_items_published ON raw_items(published_at);
CREATE INDEX idx_raw_items_fetched ON raw_items(fetched_at);

-- Labels and pain scores from classification
CREATE TABLE IF NOT EXISTS item_labels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_item_id UUID NOT NULL REFERENCES raw_items(id) ON DELETE CASCADE,
  label TEXT NOT NULL CHECK (label IN ('PAIN', 'DISCUSSION', 'NEWS', 'OTHER')),
  confidence NUMERIC(4,3) CHECK (confidence >= 0 AND confidence <= 1),
  pain_score NUMERIC(5,2) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(raw_item_id)
);

CREATE INDEX idx_item_labels_raw ON item_labels(raw_item_id);

-- Clusters (pain themes per day)
CREATE TABLE IF NOT EXISTS clusters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL,
  cluster_index INT NOT NULL,
  title TEXT,
  summary TEXT,
  persona TEXT,
  why_matters TEXT,
  size INT DEFAULT 0,
  score NUMERIC(6,2) DEFAULT 0,
  top_terms TEXT[],
  example_urls JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(date, cluster_index)
);

CREATE INDEX idx_clusters_date ON clusters(date);

-- Which raw items belong to which cluster
CREATE TABLE IF NOT EXISTS cluster_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cluster_id UUID NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
  raw_item_id UUID NOT NULL REFERENCES raw_items(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(cluster_id, raw_item_id)
);

CREATE INDEX idx_cluster_items_cluster ON cluster_items(cluster_id);

-- Daily newsletter markdown
CREATE TABLE IF NOT EXISTS daily_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL UNIQUE,
  markdown_content TEXT,
  generated_at TIMESTAMPTZ DEFAULT now()
);

-- Catalyst items (industry news bullets per day)
CREATE TABLE IF NOT EXISTS catalyst_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL,
  title TEXT,
  summary TEXT,
  interests JSONB DEFAULT '[]',
  problems_created TEXT,
  source_urls JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_catalyst_items_date ON catalyst_items(date);

-- Optional: store embeddings for items (if using Gemini embeddings)
CREATE TABLE IF NOT EXISTS item_embeddings (
  raw_item_id UUID PRIMARY KEY REFERENCES raw_items(id) ON DELETE CASCADE,
  embedding FLOAT[],
  model TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
