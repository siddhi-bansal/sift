-- Seed interests and interest_sources (run after 001_schema.sql)
-- This is optional if you use the Python seed script; use one of the two.

INSERT INTO interests (name, description) VALUES
  ('General', 'Broad tech and product signals'),
  ('Developer Tools', 'IDEs, CLIs, dev experience, debugging'),
  ('AI / ML', 'Machine learning, LLMs, AI products'),
  ('SaaS & B2B', 'B2B software, enterprise, pricing'),
  ('Startups', 'Founder pain, fundraising, growth'),
  ('Design & UX', 'Design systems, user research, accessibility'),
  ('Data & Infra', 'Databases, data pipelines, infrastructure'),
  ('Security & Compliance', 'Security, privacy, compliance'),
  ('Marketing', 'Growth, SEO, content, ads'),
  ('Mobile', 'iOS, Android, cross-platform')
ON CONFLICT (name) DO NOTHING;

-- interest_sources: subreddits and RSS per interest
-- We use interest names to resolve IDs in a seed script; here we use subqueries.

-- General (fallback when no subscribers)
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'technology', 1.0 FROM interests WHERE name = 'General' LIMIT 1
ON CONFLICT (interest_id, source_type, source_value) DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'rss', 'https://news.ycombinator.com/rss', 1.0 FROM interests WHERE name = 'General' LIMIT 1
ON CONFLICT (interest_id, source_type, source_value) DO NOTHING;

-- Developer Tools
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'programming', 1.0 FROM interests WHERE name = 'Developer Tools' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'vscode', 1.0 FROM interests WHERE name = 'Developer Tools' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'devops', 1.0 FROM interests WHERE name = 'Developer Tools' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'rss', 'https://blog.jetbrains.com/feed/', 0.8 FROM interests WHERE name = 'Developer Tools' LIMIT 1 ON CONFLICT DO NOTHING;

-- AI / ML
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'MachineLearning', 1.0 FROM interests WHERE name = 'AI / ML' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'LocalLLaMA', 1.0 FROM interests WHERE name = 'AI / ML' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'rss', 'https://blog.google/technology/developers/feed/', 0.9 FROM interests WHERE name = 'AI / ML' LIMIT 1 ON CONFLICT DO NOTHING;

-- SaaS & B2B
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'SaaS', 1.0 FROM interests WHERE name = 'SaaS & B2B' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'startups', 0.9 FROM interests WHERE name = 'SaaS & B2B' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'rss', 'https://www.saastr.com/feed/', 0.8 FROM interests WHERE name = 'SaaS & B2B' LIMIT 1 ON CONFLICT DO NOTHING;

-- Startups
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'startups', 1.0 FROM interests WHERE name = 'Startups' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'entrepreneur', 0.9 FROM interests WHERE name = 'Startups' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'rss', 'https://www.ycombinator.com/blog/feed/', 0.9 FROM interests WHERE name = 'Startups' LIMIT 1 ON CONFLICT DO NOTHING;

-- Design & UX
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'UXDesign', 1.0 FROM interests WHERE name = 'Design & UX' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'userexperience', 1.0 FROM interests WHERE name = 'Design & UX' LIMIT 1 ON CONFLICT DO NOTHING;

-- Data & Infra
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'dataengineering', 1.0 FROM interests WHERE name = 'Data & Infra' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'aws', 0.9 FROM interests WHERE name = 'Data & Infra' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'rss', 'https://aws.amazon.com/blogs/aws/feed/', 0.8 FROM interests WHERE name = 'Data & Infra' LIMIT 1 ON CONFLICT DO NOTHING;

-- Security & Compliance
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'netsec', 1.0 FROM interests WHERE name = 'Security & Compliance' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'cybersecurity', 1.0 FROM interests WHERE name = 'Security & Compliance' LIMIT 1 ON CONFLICT DO NOTHING;

-- Marketing
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'SEO', 1.0 FROM interests WHERE name = 'Marketing' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'marketing', 1.0 FROM interests WHERE name = 'Marketing' LIMIT 1 ON CONFLICT DO NOTHING;

-- Mobile
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'iOSProgramming', 1.0 FROM interests WHERE name = 'Mobile' LIMIT 1 ON CONFLICT DO NOTHING;
INSERT INTO interest_sources (interest_id, source_type, source_value, weight)
SELECT id, 'subreddit', 'androiddev', 1.0 FROM interests WHERE name = 'Mobile' LIMIT 1 ON CONFLICT DO NOTHING;
