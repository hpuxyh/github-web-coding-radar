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

function normalizePath(value) {
  const raw = String(value || '/').trim();
  try {
    const parsed = new URL(raw, 'https://github-web-coding-radar.pages.dev');
    const pathname = parsed.pathname || '/';
    if (pathname === '/' || pathname === '/radar.html') return '/radar';
    return pathname.slice(0, 160);
  } catch {
    return raw.startsWith('/') ? raw.slice(0, 160) : '/';
  }
}

function normalizeVisitorId(value) {
  const raw = String(value || '').trim();
  return /^[a-zA-Z0-9_-]{8,96}$/.test(raw) ? raw : '';
}

export async function onRequestOptions() {
  return new Response(null, { status: 204 });
}

export async function onRequestPost({ request, env }) {
  if (!env.ANALYTICS_DB) {
    return json({ ok: false, error: 'analytics database is not configured' }, 500);
  }

  let payload = {};
  try {
    payload = await request.json();
  } catch {
    return json({ ok: false, error: 'invalid json' }, 400);
  }

  const visitorId = normalizeVisitorId(payload.visitorId);
  if (!visitorId) return json({ ok: false, error: 'missing visitor id' }, 400);

  const now = Date.now();
  const path = normalizePath(payload.path);
  const referrer = String(payload.referrer || '').slice(0, 300);
  const country = String(request.cf?.country || '').slice(0, 8);
  const userAgent = String(request.headers.get('user-agent') || '').slice(0, 240);

  await env.ANALYTICS_DB.prepare(
    `INSERT INTO analytics_events (ts, day, path, visitor_id, referrer, country, user_agent)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
  )
    .bind(now, shanghaiDay(now), path, visitorId, referrer, country, userAgent)
    .run();

  return json({ ok: true });
}
