ALTER TABLE matches ADD COLUMN match_id INTEGER;
CREATE INDEX match_id_idx ON matches (match_id);
ALTER TABLE members ADD COLUMN full_name TEXT;