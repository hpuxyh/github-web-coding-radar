const ALLOWED_ORIGINS = new Set([
  'https://hpuxyh.github.io',
  'https://github-web-coding-radar.pages.dev',
  'http://127.0.0.1:8794',
  'http://localhost:8794'
]);

const STRING_LIMIT = 360;
const NOTE_LIMIT = 520;

function corsHeaders(origin) {
  const allowedOrigin = ALLOWED_ORIGINS.has(origin) ? origin : 'https://hpuxyh.github.io';
  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400'
  };
}

function jsonResponse(body, status = 200, origin = '') {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders(origin),
      'Content-Type': 'application/json; charset=utf-8'
    }
  });
}

function cleanText(value, limit = STRING_LIMIT) {
  return String(value || '').replace(/\s+/g, ' ').trim().slice(0, limit);
}

function cleanColor(value) {
  const color = cleanText(value, 24);
  return /^#[0-9a-fA-F]{6}$/.test(color) ? color : '#09a3ff';
}

function cleanTheme(value) {
  return ['clean', 'cute', 'dark'].includes(value) ? value : 'clean';
}

function cleanCard(item) {
  return {
    title: cleanText(item?.title, 80),
    meta: cleanText(item?.meta, 80),
    note: cleanText(item?.note, NOTE_LIMIT)
  };
}

function cleanCards(value, fallback) {
  const source = Array.isArray(value) ? value : fallback;
  return source
    .slice(0, 6)
    .map(cleanCard)
    .filter((item) => item.title || item.meta || item.note)
    .slice(0, 4);
}

function cleanSiteData(value = {}) {
  const fallbackCards = [
    { title: '作品一', meta: '网页作品', note: '用一句话说明这个作品。' },
    { title: '作品二', meta: '兴趣项目', note: '这里放第二个作品。' },
    { title: '作品三', meta: '联系入口', note: '这里放联系方式或合作说明。' }
  ];
  return {
    title: cleanText(value.title, 80),
    subtitle: cleanText(value.subtitle),
    intro: cleanText(value.intro, NOTE_LIMIT),
    primary: cleanText(value.primary, 60),
    color: cleanColor(value.color),
    visualStyle: cleanTheme(value.visualStyle),
    kicker: cleanText(value.kicker, 120),
    sectionTitle: cleanText(value.sectionTitle, 80),
    skillsText: cleanText(value.skillsText, 180),
    contactTitle: cleanText(value.contactTitle, 80),
    contactNote: cleanText(value.contactNote, NOTE_LIMIT),
    cards: cleanCards(value.cards, fallbackCards),
    friends: cleanCards(value.friends, [
      { title: '朋友的小站', meta: '友链', note: '这里放朋友主页。' },
      { title: '合作伙伴', meta: '合作', note: '这里放一起做项目的人。' },
      { title: '更多链接', meta: '入口', note: '这里放更多链接。' }
    ])
  };
}

function buildPrompt(message, currentData) {
  return [
    '你是一个中文网页改造助手，用户是完全小白。',
    '你的任务：根据用户一句话，直接改造一个个人小站页面的数据。',
    '不要解释代码，不要输出 markdown，只输出 json。',
    '必须返回完整 data 对象，而不是只返回改动字段。',
    '允许修改：标题、简介、欢迎语、按钮、主色、页面风格、技能、代表作卡片、友链、联系区。',
    '页面风格 visualStyle 只能是 clean、cute、dark 三选一。',
    '颜色 color 必须是 #RRGGBB。',
    'cards 和 friends 每个保留 3 个，字段是 title、meta、note。',
    '如果用户想改成摄影、小红书选题、AI 工具榜单、餐厅选择器、作品集等，直接把页面内容整体换成对应用途。',
    'json 格式示例：',
    '{"assistantMessage":"已帮你改好。","changes":["页面变成摄影作品集"],"data":{"title":"我的摄影作品集","subtitle":"记录光和生活。","intro":"你好，我喜欢摄影。","primary":"联系约拍","color":"#ff6aa2","visualStyle":"cute","kicker":"欢迎来到我的摄影小站！","sectionTitle":"摄影作品","skillsText":"摄影 / 修图 / 街拍","contactTitle":"联系我","contactNote":"欢迎交流。","cards":[{"title":"街头光影","meta":"城市记录","note":"记录城市瞬间。"},{"title":"人像练习","meta":"约拍作品","note":"自然光人像。"},{"title":"旅行相册","meta":"照片合集","note":"旅行记录。"}],"friends":[{"title":"朋友的小站","meta":"友链","note":"朋友主页。"},{"title":"合作伙伴","meta":"合作","note":"一起做项目的人。"},{"title":"更多链接","meta":"入口","note":"更多页面。"}]}}',
    '',
    `当前页面数据 json：${JSON.stringify(currentData)}`,
    `用户想法：${message}`
  ].join('\n');
}

async function handleRemix(request, env, origin) {
  if (!env.DEEPSEEK_API_KEY) {
    return jsonResponse({ error: 'DEEPSEEK_API_KEY is not configured' }, 500, origin);
  }

  const body = await request.json();
  const message = cleanText(body?.message, 600);
  const current = cleanSiteData(body?.current || {});

  if (!message) {
    return jsonResponse({ error: 'message is required' }, 400, origin);
  }

  const deepseekResponse = await fetch('https://api.deepseek.com/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${env.DEEPSEEK_API_KEY}`
    },
    body: JSON.stringify({
      model: 'deepseek-v4-flash',
      messages: [
        {
          role: 'system',
          content:
            '你只返回严格 JSON。不要输出 markdown。不要包含代码块。所有字段都用中文自然表达。'
        },
        {
          role: 'user',
          content: buildPrompt(message, current)
        }
      ],
      thinking: { type: 'disabled' },
      response_format: { type: 'json_object' },
      temperature: 0.35,
      max_tokens: 1800,
      stream: false
    })
  });

  const deepseekBody = await deepseekResponse.json();
  if (!deepseekResponse.ok) {
    return jsonResponse(
      {
        error: 'DeepSeek request failed',
        status: deepseekResponse.status,
        detail: cleanText(deepseekBody?.error?.message, 240)
      },
      502,
      origin
    );
  }

  const content = deepseekBody?.choices?.[0]?.message?.content || '{}';
  let parsed;
  try {
    parsed = JSON.parse(content);
  } catch (error) {
    return jsonResponse({ error: 'DeepSeek did not return valid JSON' }, 502, origin);
  }

  const nextData = cleanSiteData({ ...current, ...parsed.data });
  const changes = Array.isArray(parsed.changes)
    ? parsed.changes.map((item) => cleanText(item, 120)).filter(Boolean).slice(0, 6)
    : ['DeepSeek 已根据你的描述改了页面'];

  return jsonResponse(
    {
      assistantMessage:
        cleanText(parsed.assistantMessage, 240) ||
        `已帮你改好：${changes.slice(0, 3).join('、')}。`,
      changes,
      data: nextData,
      usage: deepseekBody.usage || null
    },
    200,
    origin
  );
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    const url = new URL(request.url);
    if (request.method === 'POST' && url.pathname === '/api/remix-chat') {
      try {
        return await handleRemix(request, env, origin);
      } catch (error) {
        return jsonResponse(
          { error: 'Worker request failed', detail: cleanText(error?.message, 200) },
          500,
          origin
        );
      }
    }

    return jsonResponse({ ok: true, endpoint: '/api/remix-chat' }, 200, origin);
  }
};
