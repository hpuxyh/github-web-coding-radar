const DAY_MS = 24 * 60 * 60 * 1000;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}

function shanghaiDay(ts = Date.now()) {
  return new Date(ts + 8 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

function authOk(request, env) {
  const expected = String(env.ADMIN_KEY || '').trim();
  if (!expected) return false;
  const url = new URL(request.url);
  const queryKey = String(url.searchParams.get('key') || '').trim();
  const header = String(request.headers.get('authorization') || '').trim();
  const bearer = header.toLowerCase().startsWith('bearer ') ? header.slice(7).trim() : '';
  return queryKey === expected || bearer === expected;
}

function rowOrZero(row) {
  return {
    pageviews: Number(row?.pageviews || 0),
    visitors: Number(row?.visitors || 0),
  };
}

export async function onRequestGet({ request, env }) {
  if (!env.ANALYTICS_DB) {
    return json({ ok: false, error: 'analytics database is not configured' }, 500);
  }
  if (!authOk(request, env)) return json({ ok: false, error: 'unauthorized' }, 401);

  const url = new URL(request.url);
  const days = Math.max(1, Math.min(90, Number(url.searchParams.get('days') || 30)));
  const today = shanghaiDay();
  const startDay = shanghaiDay(Date.now() - (days - 1) * DAY_MS);

  const [total, todayRow, daily, paths, countries, recent] = await Promise.all([
    env.ANALYTICS_DB.prepare(
      `SELECT COUNT(*) AS pageviews, COUNT(DISTINCT visitor_id) AS visitors
       FROM analytics_events`,
    ).first(),
    env.ANALYTICS_DB.prepare(
      `SELECT COUNT(*) AS pageviews, COUNT(DISTINCT visitor_id) AS visitors
       FROM analytics_events
       WHERE day = ?`,
    )
      .bind(today)
      .first(),
    env.ANALYTICS_DB.prepare(
      `SELECT day, COUNT(*) AS pageviews, COUNT(DISTINCT visitor_id) AS visitors
       FROM analytics_events
       WHERE day >= ?
       GROUP BY day
       ORDER BY day DESC`,
    )
      .bind(startDay)
      .all(),
    env.ANALYTICS_DB.prepare(
      `SELECT path, COUNT(*) AS pageviews, COUNT(DISTINCT visitor_id) AS visitors
       FROM analytics_events
       WHERE day >= ?
       GROUP BY path
       ORDER BY pageviews DESC
       LIMIT 20`,
    )
      .bind(startDay)
      .all(),
    env.ANALYTICS_DB.prepare(
      `SELECT COALESCE(NULLIF(country, ''), '未知') AS country, COUNT(*) AS pageviews,
              COUNT(DISTINCT visitor_id) AS visitors
       FROM analytics_events
       WHERE day >= ?
       GROUP BY country
       ORDER BY pageviews DESC
       LIMIT 20`,
    )
      .bind(startDay)
      .all(),
    env.ANALYTICS_DB.prepare(
      `SELECT ts, day, path, COALESCE(NULLIF(country, ''), '未知') AS country, referrer
       FROM analytics_events
       ORDER BY ts DESC
       LIMIT 30`,
    ).all(),
  ]);

  return json({
    ok: true,
    timezone: 'Asia/Shanghai',
    generatedAt: new Date().toISOString(),
    days,
    total: rowOrZero(total),
    today: rowOrZero(todayRow),
    daily: daily.results || [],
    paths: paths.results || [],
    countries: countries.results || [],
    recent: recent.results || [],
  });
}
