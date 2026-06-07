const assetPath = (path) => `${import.meta.env.BASE_URL}${path}`;

export const assets = {
  hero: assetPath('assets/portfolio-hero.png'),
};

export const profile = {
  name: '我的项目合集',
  handle: '持续更新中',
  role: '想法试验 / 日常工具 / 内容整理',
  githubUrl: 'https://github.com/hpuxyh',
  headline: '这里放我做过的项目：每个项目做什么、能不能直接用、代码在哪里。',
  intro:
    '我把重点项目、可直接使用的页面、更多项目入口都整理在一起。不是写给程序员看的清单，而是让普通用户也能快速知道：这个东西有什么用，点哪里可以看。',
};

export const githubSnapshot = {
  capturedAt: '2026-06-07',
  sourceUrl: 'https://github.com/hpuxyh?tab=repositories',
};

export const projects = [
  {
    id: 'github-remix-mvp',
    name: '把好项目改成我的作品',
    repoName: 'github-web-coding-radar',
    type: '新手做网页作品',
    category: 'content',
    status: '可以使用',
    publishedAt: '2026-06-07',
    repoUrl: 'https://github.com/hpuxyh/github-web-coding-radar',
    liveUrl: './remix-mvp.html',
    problem:
      '普通人打开 GitHub 容易迷路：不知道哪个项目能改，也不知道怎么改成自己的网页作品。',
    preview: {
      title: '选一个项目照着改',
      subtitle: '找项目、看示例、直接编辑、看我的前端',
      items: ['适合新手', '示例前端', '直接编辑', '我的版本'],
    },
    summary:
      '帮你先挑适合新手的 GitHub 项目，再一步步改成个人主页、清单页面或选择工具。',
    details:
      '页面用白话说明这个项目能改成什么，也能先打开示例前端；用户在网页里修改内容后，还能打开自己的前端版本查看效果。',
    techIntro:
      '先用静态页面验证“找项目、看示例、网页里改、看我的版本”这条路能不能跑通，后续再接真实项目和公开作品审核。',
    tags: ['新手可用', '示例前端', '直接编辑', '网页作品'],
    accent: '#1769c2',
    featured: true,
  },
  {
    id: 'github-remix-community',
    name: '为什么做这个网站',
    repoName: 'github-web-coding-radar',
    type: '白话说明',
    category: 'content',
    status: '可以阅读',
    publishedAt: '2026-06-07',
    repoUrl: 'https://github.com/hpuxyh/github-web-coding-radar',
    liveUrl: './remix-community.html',
    problem:
      '很多人想用 AI 做网页作品，但一打开 GitHub 就不知道该看什么、该怎么改。',
    preview: {
      title: '为什么值得做',
      subtitle: '把 GitHub 好项目变成普通人能用的作品',
      items: ['为什么做', '谁会用', '怎么开始', '能做出来吗'],
    },
    summary:
      '这页用白话解释：为什么要帮普通人从 GitHub 找项目，并一步步改成自己的作品。',
    details:
      '它回答几个问题：这个网站解决什么问题，为什么现在值得做，第一版应该先帮用户完成哪几步。',
    techIntro:
      '先从每天找项目和白话解释开始，再逐步增加站内编辑、作品保存、作品展示这些能力。',
    tags: ['白话说明', '新手做作品', 'GitHub 项目', '为什么做'],
    accent: '#1d6fae',
    featured: true,
  },
  {
    id: 'expert-sources-radar',
    name: '人物关注项目雷达',
    repoName: 'github-web-coding-radar',
    type: '趋势观察工具',
    category: 'content',
    status: '可以使用',
    publishedAt: '2026-06-07',
    repoUrl: 'https://github.com/hpuxyh/github-web-coding-radar',
    liveUrl: 'https://github-web-coding-radar.pages.dev/?v=expert-sources-6b964f3',
    problem:
      '只看项目热度还不够，有些早期线索要看哪些人正在关注、引用和讨论。',
    preview: {
      title: '人物信号清单',
      subtitle: '看谁在关注什么项目',
      items: ['人物信号', '前沿趋势', '产品灵感', '内容选题'],
    },
    summary:
      '它会把公开的人物关注信号和项目热度放在一起，帮你判断哪些项目值得提前看。',
    details:
      '适合用来做更细的选题：哪些项目被关键人物提到、为什么值得观察、适合写成什么内容。',
    techIntro:
      '背后做法是先收集公开关注线索，再和项目热度、更新情况一起整理成网页榜单。',
    tags: ['人物信号', '趋势观察', '项目选题', '提前发现'],
    accent: '#d94686',
    featured: true,
  },
  {
    id: 'github-web-coding-radar',
    name: '每日好项目雷达',
    repoName: 'github-web-coding-radar',
    type: '内容选题工具',
    category: 'content',
    status: '可以使用',
    publishedAt: '2026-06-06',
    repoUrl: 'https://github.com/hpuxyh/github-web-coding-radar',
    liveUrl: 'https://github-web-coding-radar.pages.dev/',
    problem:
      '每天网上都会冒出很多新工具，一个个找很费时间，也很容易错过真正有意思的项目。',
    preview: {
      title: '每日项目清单',
      subtitle: '自动找项目，帮你先筛一遍',
      items: ['发现新工具', '整理亮点', '生成文案', '网页查看'],
    },
    summary:
      '它会每天自动整理一批值得关注的新项目，并把适合发内容的亮点写出来。',
    details:
      '适合用来做选题池：今天有什么新工具、哪个项目值得试、可以怎么介绍，都能先有一版草稿。',
    techIntro:
      '背后是一个自动整理流程：定时去公开项目页面找线索，再把项目亮点、介绍文案和查看页面整理出来。',
    tags: ['自动找项目', '内容选题', '每日整理', '小红书草稿'],
    accent: '#2f80ed',
    featured: true,
  },
  {
    id: 'ppt-html',
    name: '幻灯片转网页',
    repoName: 'PPT-HTML-',
    type: '演示页工具',
    category: 'content',
    status: '可以使用',
    publishedAt: '2026-06-05',
    repoUrl: 'https://github.com/hpuxyh/PPT-HTML-',
    liveUrl: 'https://hpuxyh.github.io/PPT-HTML-/',
    problem:
      '做完一份演示内容后，经常还要反复导出、调整格式、发文件，很麻烦。',
    cover: assetPath('assets/project-covers/ppt-html-cover.png'),
    coverAlt: '幻灯片转网页的预览封面',
    screenshots: [
      { src: assetPath('assets/projects/ppt-html-preview.png'), alt: '幻灯片转网页的预览页' },
      { src: assetPath('assets/projects/ppt-html-introducing.png'), alt: '幻灯片转网页的介绍页' },
    ],
    summary:
      '把演示内容变成网页，别人打开链接就能看，不用下载文件。',
    details:
      '适合把文字大纲、演讲稿或演示材料快速变成一个能直接分享的网页版本。',
    techIntro:
      '背后做法是把每页内容拆成网页小模块，再统一排版和发布。',
    tags: ['演示分享', '网页展示', '不用下载', '方便转发'],
    accent: '#ff7a59',
    featured: true,
  },
  {
    id: 'no-choice',
    name: '不做选择',
    repoName: 'no-choice',
    type: '日常决策工具',
    category: 'product',
    status: '可以使用',
    publishedAt: '2026-06-03',
    repoUrl: 'https://github.com/hpuxyh/no-choice',
    liveUrl: 'https://no-choice.pages.dev/play',
    problem:
      '今晚吃什么、周末去哪、送什么礼物，这些小选择不大，但很容易耗时间。',
    cover: assetPath('assets/project-covers/no-choice-cover.png'),
    coverAlt: '不做选择的输入和结果页面',
    screenshots: [
      { src: assetPath('assets/projects/no-choice-web.png'), alt: '不做选择的网页首页' },
      { src: assetPath('assets/projects/no-choice-mobile.png'), alt: '不做选择的手机页面' },
      { src: assetPath('assets/projects/no-choice-draw.png'), alt: '不做选择的结果页' },
    ],
    summary:
      '把选择困难交给它，输入你的情况，它直接帮你给出一个可以执行的答案。',
    details:
      '它不是让你继续纠结，而是把几个候选项摆出来，最后推你往前走一步。',
    techIntro:
      '背后做法是先收集你的需求，再把候选项整理成卡片，最后给出清楚的建议。',
    tags: ['选择困难', '吃什么', '去哪玩', '快速拍板'],
    accent: '#2f80ed',
    featured: true,
  },
  {
    id: 'no-choice-lite',
    name: '不做选择轻量版',
    repoName: 'no-choice-lite',
    type: '简洁版工具',
    category: 'product',
    status: '可以使用',
    publishedAt: '2026-06-03',
    repoUrl: 'https://github.com/hpuxyh/no-choice-lite',
    liveUrl: 'https://no-choice-lite.pages.dev/play',
    problem:
      '有些用户只想快速得到答案，不想看复杂玩法或太多装饰。',
    cover: assetPath('assets/project-covers/no-choice-lite-cover.png'),
    coverAlt: '不做选择轻量版的首页',
    screenshots: [
      { src: assetPath('assets/projects/no-choice-lite-home.png'), alt: '不做选择轻量版首页' },
      { src: assetPath('assets/projects/no-choice-mobile.png'), alt: '不做选择的手机流程参考' },
    ],
    summary:
      '保留“不做选择”的核心功能，把页面做得更轻、更直接。',
    details:
      '适合手机上快速用：少看说明，少做操作，直接进入拍板流程。',
    techIntro:
      '背后做法是沿用主项目的判断流程，把页面和操作步骤重新做得更简洁。',
    tags: ['手机可用', '更简洁', '快速开始', '少步骤'],
    accent: '#21a67a',
    featured: true,
  },
  {
    id: 'taste-lens',
    name: '拍照尝味道',
    repoName: 'taste-lens-mvp',
    type: '食物判断工具',
    category: 'product',
    status: '可以使用',
    publishedAt: '2026-06-02',
    repoUrl: 'https://github.com/hpuxyh/taste-lens-mvp',
    liveUrl: 'https://hpuxyh.github.io/taste-lens-mvp/',
    problem:
      '看到一张食物图片时，很难提前判断它大概是什么味道、自己会不会喜欢。',
    cover: assetPath('assets/project-covers/taste-lens-cover.png'),
    coverAlt: '拍照尝味道的食物分析页面',
    screenshots: [
      { src: assetPath('assets/projects/taste-lens-home.png'), alt: '拍照尝味道的网页预览' },
      { src: assetPath('assets/projects/taste-lens-mobile.png'), alt: '拍照尝味道的手机分析页' },
    ],
    summary:
      '上传食物图片后，它会用白话告诉你可能的味道、口感和喜欢概率。',
    details:
      '适合用来验证一个想法：看图能不能先大概判断食物是不是合胃口。',
    techIntro:
      '背后做法是让智能识图先看食物照片，再把结果翻译成普通人能看懂的味道描述。',
    tags: ['看图判断', '食物味道', '口感提示', '喜欢概率'],
    accent: '#f5a623',
    featured: true,
  },
  {
    id: 'product-radar',
    name: '产品灵感雷达',
    repoName: 'product-radar',
    type: '灵感整理工具',
    category: 'content',
    status: '代码已公开',
    publishedAt: '2026-05-29',
    repoUrl: 'https://github.com/hpuxyh/product-radar',
    liveUrl: '',
    problem:
      '新产品、新工具、新想法太多，靠手工收集很慢，也很难持续追踪。',
    cover: assetPath('assets/project-covers/product-radar-cover.png'),
    coverAlt: '产品灵感雷达的线索看板',
    screenshots: [
      { src: assetPath('assets/projects/product-radar-scout.png'), alt: '产品灵感雷达的本地页面' },
      { src: assetPath('assets/projects/product-radar-web.png'), alt: '产品灵感雷达的中文网页' },
      { src: assetPath('assets/projects/product-radar-en.png'), alt: '产品灵感雷达的英文网页' },
    ],
    summary:
      '把每天值得看的新产品和新工具整理成卡片，方便后续试用、改造或写成内容。',
    details:
      '它更像一个灵感收集箱：先帮你把线索捞出来，再按价值和可尝试程度排好。',
    techIntro:
      '背后做法是自动查看多个公开信息来源，再把有用线索整理成中文卡片和存档。',
    tags: ['灵感收集', '新产品', '新工具', '每日整理'],
    accent: '#00a6d6',
    featured: false,
  },
  {
    id: 'jisi-ai-multi-model-qa',
    name: '集思多答案对比',
    repoName: 'jisi-ai-multi-model-qa',
    type: '问答对比工具',
    category: 'product',
    status: '代码已公开',
    publishedAt: '2026-05-17',
    repoUrl: 'https://github.com/hpuxyh/jisi-ai-multi-model-qa',
    liveUrl: '',
    problem:
      '只问一个智能助手，回答可能会偏；多看几个答案，更容易发现哪个思路靠谱。',
    preview: {
      title: '一题多答对比台',
      subtitle: '同一个问题，看看不同回答',
      items: ['同时提问', '并排查看', '找出差异', '整理结论'],
    },
    summary:
      '输入一个问题后，让多个智能助手同时回答，方便横向比较。',
    details:
      '适合写作、研究或做决定前使用：先多看几个角度，再整理出自己的判断。',
    techIntro:
      '背后做法是把同一个问题发给多个回答来源，再把结果放在同一个页面里对比。',
    tags: ['多答案对比', '写作参考', '研究辅助', '判断思路'],
    accent: '#8b5cf6',
    featured: false,
  },
];

export const repoCatalog = [
  {
    name: '把好项目改成我的作品',
    description: '帮普通人从 GitHub 选项目，照着改成自己的网页作品。',
    language: '新手工具',
    updatedAt: '2026-06-07',
    kind: '我的项目',
    repoUrl: './remix-mvp.html',
    highlighted: true,
  },
  {
    name: '为什么做这个网站',
    description: '用白话说明为什么要帮普通人把 GitHub 项目改成自己的作品。',
    language: '白话说明',
    updatedAt: '2026-06-07',
    kind: '我的项目',
    repoUrl: './remix-community.html',
    highlighted: true,
  },
  {
    name: '每日好项目雷达',
    description: '每天帮你找值得关注的新项目。',
    language: '内容工具',
    updatedAt: '2026-06-06',
    kind: '我的项目',
    repoUrl: 'https://github.com/hpuxyh/github-web-coding-radar',
    highlighted: true,
  },
  {
    name: '不做选择',
    description: '替选择困难场景直接拍板的日常工具。',
    language: '网页工具',
    updatedAt: '2026-06-06',
    kind: '我的项目',
    repoUrl: 'https://github.com/hpuxyh/no-choice',
    highlighted: true,
  },
  {
    name: '产品灵感雷达',
    description: '每天整理新产品、新工具和可改造的线索。',
    language: '内容工具',
    updatedAt: '2026-06-05',
    kind: '我的项目',
    repoUrl: 'https://github.com/hpuxyh/product-radar',
    highlighted: true,
  },
  {
    name: '设计工具参考',
    description: '一个开源设计工具的参考版本，用来看别人怎么做。',
    language: '参考资料',
    updatedAt: '2026-06-05',
    kind: '参考资料',
    repoUrl: 'https://github.com/hpuxyh/open-design',
    highlighted: false,
  },
  {
    name: '幻灯片转网页',
    description: '把演示内容变成可以直接打开的网页。',
    language: '演示工具',
    updatedAt: '2026-06-04',
    kind: '我的项目',
    repoUrl: 'https://github.com/hpuxyh/PPT-HTML-',
    highlighted: true,
  },
  {
    name: '不做选择轻量版',
    description: '更简洁、更适合手机快速使用的选择工具。',
    language: '网页工具',
    updatedAt: '2026-06-02',
    kind: '我的项目',
    repoUrl: 'https://github.com/hpuxyh/no-choice-lite',
    highlighted: true,
  },
  {
    name: '拍照尝味道',
    description: '看食物图片，猜它可能是什么味道。',
    language: '网页工具',
    updatedAt: '2026-06-01',
    kind: '我的项目',
    repoUrl: 'https://github.com/hpuxyh/taste-lens-mvp',
    highlighted: true,
  },
  {
    name: '集思多答案对比',
    description: '同一个问题，让多个智能助手一起回答并对比。',
    language: '问答工具',
    updatedAt: '2026-05-17',
    kind: '我的项目',
    repoUrl: 'https://github.com/hpuxyh/jisi-ai-multi-model-qa',
    highlighted: true,
  },
  {
    name: '后台页面模板',
    description: '用于学习后台管理页面长什么样、怎么组织。',
    language: '参考模板',
    updatedAt: '2025-03-20',
    kind: '参考资料',
    repoUrl: 'https://github.com/hpuxyh/flowbite-admin-template',
    highlighted: false,
  },
  {
    name: '早期实验一',
    description: '早期练习项目，先归档保留。',
    language: '早期练习',
    updatedAt: '2023-11-07',
    kind: '早期练习',
    repoUrl: 'https://github.com/hpuxyh/archive-dd',
    highlighted: false,
  },
  {
    name: '早期实验二',
    description: '早期练习项目，先归档保留。',
    language: '早期练习',
    updatedAt: '2023-11-07',
    kind: '早期练习',
    repoUrl: 'https://github.com/hpuxyh/archive-001',
    highlighted: false,
  },
  {
    name: '好友页面练习',
    description: '早期做过的好友页面或小页面练习。',
    language: '早期练习',
    updatedAt: '2022-08-14',
    kind: '早期练习',
    repoUrl: 'https://github.com/hpuxyh/archive-friends',
    highlighted: false,
  },
  {
    name: '阅读页面练习',
    description: '早期做过的阅读或文字页面练习。',
    language: '早期练习',
    updatedAt: '2022-08-14',
    kind: '早期练习',
    repoUrl: 'https://github.com/hpuxyh/archive-read',
    highlighted: false,
  },
  {
    name: '自学资料',
    description: '一本自学资料的收藏和学习记录。',
    language: '学习资料',
    updatedAt: '2022-08-11',
    kind: '参考资料',
    repoUrl: 'https://github.com/hpuxyh/self-learning-craft',
    highlighted: false,
  },
  {
    name: '代码托管学习记录',
    description: '早期学习如何管理和保存代码的记录。',
    language: '学习记录',
    updatedAt: '2022-03-12',
    kind: '早期练习',
    repoUrl: 'https://github.com/hpuxyh/archive-github-notes',
    highlighted: false,
  },
  {
    name: '早期实验三',
    description: '早期练习项目，先归档保留。',
    language: '早期练习',
    updatedAt: '2022-02-07',
    kind: '早期练习',
    repoUrl: 'https://github.com/hpuxyh/archive-000001',
    highlighted: false,
  },
  {
    name: '早期实验四',
    description: '早期练习项目，先归档保留。',
    language: '早期练习',
    updatedAt: '2022-02-07',
    kind: '早期练习',
    repoUrl: 'https://github.com/hpuxyh/archive-11111',
    highlighted: false,
  },
  {
    name: '飞机大战练习',
    description: '早期仿做小游戏，用来练习手机游戏开发。',
    language: '游戏练习',
    updatedAt: '2013-09-07',
    kind: '参考资料',
    repoUrl: 'https://github.com/hpuxyh/cocos2d-plane-war',
    highlighted: false,
  },
];
