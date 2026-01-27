-- RLS for frontend (anon): signup + preview
-- Run after 001_schema.sql

ALTER TABLE interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscribers ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriber_interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "interests_select_anon" ON interests FOR SELECT TO anon USING (true);
CREATE POLICY "subscribers_insert_anon" ON subscribers FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "subscriber_interests_insert_anon" ON subscriber_interests FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "subscriber_interests_delete_anon" ON subscriber_interests FOR DELETE TO anon USING (true);
CREATE POLICY "daily_reports_select_anon" ON daily_reports FOR SELECT TO anon USING (true);
