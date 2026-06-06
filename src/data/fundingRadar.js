export const fundingRadar = {
  title: '中美 AI 硬件融资周报',
  kicker: 'Funding Radar',
  subtitle: '个人版机器人/AI 硬件资金流向雷达',
  description:
    '每周追踪公开融资报道、SEC/新闻候选源和重点公司观察池，用确认后的事件判断资金是否更快、更大、更集中地流向机器人和 AI 硬件。',
  cadence: '每周一更新',
  publicPositioning: '公开页面展示趋势和判断，原始候选新闻与待确认数据保留在项目数据目录。',
  verdictWhenEmpty: '当前是 MVP 初始周报骨架，等待首批确认事件进入统计。',
  sectors: [
    { id: 'humanoid_robotics', label: '人形机器人', accent: '#2f80ed' },
    { id: 'embodied_ai', label: '具身智能', accent: '#21a67a' },
    { id: 'robot_components', label: '核心部件', accent: '#ff7a59' },
    { id: 'industrial_robotics', label: '工业机器人', accent: '#8b5cf6' },
    { id: 'warehouse_robotics', label: '仓储物流', accent: '#d94686' },
    { id: 'ai_chip_edge', label: 'AI 芯片/边缘计算', accent: '#f5a623' },
  ],
  sourcePipelines: [
    {
      label: '公开新闻候选',
      status: '自动抓取',
      detail: 'GDELT + 中英文关键词，用于发现可能的融资报道。',
    },
    {
      label: '人工确认事件',
      status: '进入统计',
      detail: '确认金额、轮次、投资方和来源链接后，才计入公开周报。',
    },
    {
      label: '公司观察池',
      status: '持续追踪',
      detail: '先盯 100-200 家重点公司，逐步补充招聘、订单和产业资本信号。',
    },
    {
      label: '公开发布',
      status: '每周归档',
      detail: 'GitHub Actions 生成快照，Cloudflare Pages/GitHub Pages 负责公开访问。',
    },
  ],
  qualityRules: [
    '金额和轮次必须有来源链接',
    '未披露金额只计事件数，不计金额总额',
    '候选新闻不直接进入统计',
    '中美口径分开看，再做总览判断',
  ],
};
