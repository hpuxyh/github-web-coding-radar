CREATE TABLE IF NOT EXISTS analytics_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  day TEXT NOT NULL,
  path TEXT NOT NULL,
  visitor_id TEXT NOT NULL,
  referrer TEXT,
  country TEXT,
  user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_analytics_events_day ON analytics_events(day);
CREATE INDEX IF NOT EXISTS idx_analytics_events_path ON analytics_events(path);
CREATE INDEX IF NOT EXISTS idx_analytics_events_visitor_day ON analytics_events(visitor_id, day);
