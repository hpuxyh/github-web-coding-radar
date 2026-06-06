import React, { useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUpRight,
  BadgeDollarSign,
  BarChart3,
  BookOpen,
  BriefcaseBusiness,
  CalendarDays,
  CheckCircle2,
  Code2,
  Database,
  ExternalLink,
  FileClock,
  GitFork,
  Github,
  Globe2,
  Layers3,
  LineChart,
  Rocket,
  Search,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { assets, githubSnapshot, profile, projects, repoCatalog } from './data/projects.js';
import { fundingRadar } from './data/fundingRadar.js';
import { fundingWeeklySnapshot } from './data/fundingWeeklySnapshot.js';

const filters = [
  { id: 'all', label: '全部' },
  { id: 'live', label: '能直接用' },
  { id: 'product', label: '日常工具' },
  { id: 'content', label: '内容整理' },
];

const dateFormatter = new Intl.DateTimeFormat('zh-CN', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

function formatDate(date) {
  return dateFormatter.format(new Date(`${date}T00:00:00`));
}

function formatUsd(value) {
  if (!value) return '待确认';
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(0)}M`;
  return `$${Math.round(value).toLocaleString('en-US')}`;
}

function formatCount(value, emptyText = '待确认') {
  if (!value) return emptyText;
  return Number(value).toLocaleString('zh-CN');
}

function openExternal(url) {
  if (!url) return;
  window.open(url, '_blank', 'noopener,noreferrer');
}

function App() {
  const [activeFilter, setActiveFilter] = useState('all');

  const sortedProjects = useMemo(
    () =>
      [...projects].sort(
        (a, b) => new Date(b.publishedAt) - new Date(a.publishedAt),
      ),
    [],
  );

  const filteredProjects = useMemo(() => {
    return sortedProjects.filter((project) => {
      if (activeFilter === 'live') return Boolean(project.liveUrl);
      if (activeFilter === 'product') return project.category === 'product';
      if (activeFilter === 'content') return project.category === 'content';
      return true;
    });
  }, [activeFilter, sortedProjects]);

  const liveCount = projects.filter((project) => project.liveUrl).length;
  const ownRepoCount = repoCatalog.filter((repo) => repo.kind === '我的项目').length;

  return (
    <main className="site-shell">
      <Header />

      <section
        className="hero"
        id="top"
        aria-labelledby="hero-title"
        style={{ '--hero-image': `url("${assets.hero}")` }}
      >
        <div className="hero-content">
          <div className="eyebrow">
            <Sparkles size={16} aria-hidden="true" />
            <span>个人项目合集</span>
          </div>
          <h1 id="hero-title">{profile.name}</h1>
          <p className="hero-role">{profile.role}</p>
          <p className="hero-copy">{profile.headline}</p>
          <p className="hero-intro">{profile.intro}</p>

          <div className="hero-actions" aria-label="主要入口">
            <a className="primary-action" href="#projects">
              <Rocket size={18} aria-hidden="true" />
              看项目
            </a>
            <a className="secondary-action" href="#funding">
              <LineChart size={18} aria-hidden="true" />
              融资周报
            </a>
            <button
              className="icon-action"
              type="button"
              title="打开代码主页"
              aria-label="打开代码主页"
              onClick={() => openExternal(profile.githubUrl)}
            >
              <Github size={20} aria-hidden="true" />
            </button>
          </div>

          <dl className="hero-metrics" aria-label="项目概览">
            <div>
              <dt>{projects.length}</dt>
              <dd>重点项目</dd>
            </div>
            <div>
              <dt>{repoCatalog.length}</dt>
              <dd>更多入口</dd>
            </div>
            <div>
              <dt>{liveCount}</dt>
              <dd>能直接用</dd>
            </div>
          </dl>
        </div>
        <a className="scroll-cue" href="#funding" aria-label="跳到融资周报">
          <ArrowDown size={18} aria-hidden="true" />
        </a>
      </section>

      <FundingRadarSection />

      <section className="section-band project-band" id="projects">
        <div className="section-inner">
          <SectionHeading
            kicker="重点项目"
            title="先看这些项目"
            copy="每张卡片都尽量用白话讲清楚：它解决什么问题、可以怎么用、点哪里能看到。"
          />

          <div className="toolbar" aria-label="项目筛选">
            <div className="filter-label">
              <Search size={16} aria-hidden="true" />
              <span>筛选</span>
            </div>
            <div className="filter-tabs" role="tablist" aria-label="项目筛选">
              {filters.map((filter) => (
                <button
                  key={filter.id}
                  className={activeFilter === filter.id ? 'active' : ''}
                  type="button"
                  role="tab"
                  aria-selected={activeFilter === filter.id}
                  onClick={() => setActiveFilter(filter.id)}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>

          <div className="project-grid">
            {filteredProjects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        </div>
      </section>

      <section className="section-band catalog-band" id="catalog">
        <div className="section-inner">
          <SectionHeading
            kicker="更多项目"
            title="全部项目入口"
            copy={`这里整理了 ${repoCatalog.length} 个公开项目入口，其中 ${ownRepoCount} 个是我的项目；整理日期 ${formatDate(githubSnapshot.capturedAt)}。`}
          />
          <div className="repo-catalog" aria-label="全部项目入口">
            {repoCatalog.map((repo) => (
              <RepositoryRow key={repo.name} repo={repo} />
            ))}
          </div>
        </div>
      </section>

      <section className="section-band timeline-band" id="timeline">
        <div className="section-inner timeline-layout">
          <SectionHeading
            kicker="发布时间线"
            title="更新顺序"
            copy="按项目整理和发布的时间排列，方便看最近先做了什么。"
          />
          <div className="timeline" aria-label="项目发布时间线">
            {sortedProjects.map((project, index) => (
              <button
                className="timeline-item"
                key={project.id}
                type="button"
                onClick={() => {
                  document
                    .getElementById(project.id)
                    ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }}
              >
                <span className="timeline-marker" style={{ '--accent': project.accent }}>
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="timeline-main">
                  <span className="timeline-date">
                    <CalendarDays size={15} aria-hidden="true" />
                    {formatDate(project.publishedAt)}
                  </span>
                  <strong>{project.name}</strong>
                  <span>{project.summary}</span>
                </span>
                <ArrowUpRight size={18} aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>
      </section>

      <footer className="site-footer">
        <span>{profile.handle}</span>
        <a href={profile.githubUrl} target="_blank" rel="noreferrer">
          代码主页
        </a>
      </footer>
    </main>
  );
}

function Header() {
  return (
    <header className="site-header">
      <a className="brand" href="#top" aria-label="回到首页">
        <span className="brand-mark">项</span>
        <span>{profile.handle}</span>
      </a>
      <nav aria-label="主导航">
        <a href="#funding">融资周报</a>
        <a href="#projects">项目</a>
        <a href="#catalog">更多</a>
        <a href="#timeline">顺序</a>
        <a href={profile.githubUrl} target="_blank" rel="noreferrer">
          代码主页
        </a>
      </nav>
    </header>
  );
}

function FundingRadarSection() {
  const snapshot = fundingWeeklySnapshot;
  const metrics = snapshot.metrics;
  const maxTrend = Math.max(...snapshot.trends.map((item) => item.events), 1);
  const watchlistTotal =
    metrics.watchlistCompanies ||
    Object.values(snapshot.watchlistCounts || {}).reduce((total, count) => total + count, 0);

  const statCards = [
    {
      label: '本周确认融资',
      value: formatCount(metrics.events),
      detail: '只统计人工确认事件',
      icon: CheckCircle2,
      tone: '#21a67a',
    },
    {
      label: '披露金额',
      value: formatUsd(metrics.amountUsd),
      detail: '未披露金额不计入总额',
      icon: BadgeDollarSign,
      tone: '#2f80ed',
    },
    {
      label: '中美事件',
      value: `${formatCount(metrics.chinaEvents, '0')} / ${formatCount(metrics.usEvents, '0')}`,
      detail: '中国 / 美国',
      icon: Globe2,
      tone: '#ff7a59',
    },
    {
      label: '候选新闻',
      value: formatCount(snapshot.candidateStats.count, '0'),
      detail: '自动抓取，等待筛选',
      icon: FileClock,
      tone: '#8b5cf6',
    },
  ];

  return (
    <section className="section-band funding-band" id="funding">
      <div className="section-inner funding-inner">
        <SectionHeading
          kicker={fundingRadar.kicker}
          title={fundingRadar.title}
          copy={fundingRadar.description}
        />

        <div className="funding-topline">
          <div className="funding-intro">
            <span className="funding-pill">
              <CalendarDays size={15} aria-hidden="true" />
              {snapshot.week.label} · {formatDate(snapshot.week.start)} - {formatDate(snapshot.week.end)}
            </span>
            <h3>{fundingRadar.subtitle}</h3>
            <p>{snapshot.status === 'empty' ? fundingRadar.verdictWhenEmpty : '本周快照已更新。'}</p>
            <div className="funding-rules" aria-label="统计规则">
              {fundingRadar.qualityRules.map((rule) => (
                <span key={rule}>
                  <ShieldCheck size={14} aria-hidden="true" />
                  {rule}
                </span>
              ))}
            </div>
            {snapshot.candidateStats.errors?.length > 0 && (
              <div className="funding-source-note">
                <FileClock size={16} aria-hidden="true" />
                候选源本次没有稳定返回，已记录 {snapshot.candidateStats.errors.length} 条源错误。
              </div>
            )}
          </div>

          <div className="funding-score">
            <span>观察池</span>
            <strong>{watchlistTotal}</strong>
            <p>
              CN {snapshot.watchlistCounts.CN || 0} · US {snapshot.watchlistCounts.US || 0}
            </p>
          </div>
        </div>

        <div className="funding-stat-grid">
          {statCards.map((card) => {
            const Icon = card.icon;
            return (
              <div className="funding-stat" key={card.label} style={{ '--tone': card.tone }}>
                <span className="funding-stat-icon">
                  <Icon size={19} aria-hidden="true" />
                </span>
                <span>{card.label}</span>
                <strong>{card.value}</strong>
                <em>{card.detail}</em>
              </div>
            );
          })}
        </div>

        <div className="funding-grid">
          <div className="funding-panel">
            <div className="panel-title">
              <BarChart3 size={19} aria-hidden="true" />
              <h3>12 周事件趋势</h3>
            </div>
            <div className="trend-bars" aria-label="过去 12 周融资事件趋势">
              {snapshot.trends.map((item) => (
                <div className="trend-bar" key={item.week}>
                  <i style={{ '--bar-height': `${Math.max(8, (item.events / maxTrend) * 100)}%` }} />
                  <span>{item.label}</span>
                  <strong>{item.events}</strong>
                </div>
              ))}
            </div>
          </div>

          <div className="funding-panel">
            <div className="panel-title">
              <Database size={19} aria-hidden="true" />
              <h3>数据管线</h3>
            </div>
            <div className="pipeline-list">
              {fundingRadar.sourcePipelines.map((item, index) => (
                <div className="pipeline-row" key={item.label}>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <div>
                    <strong>{item.label}</strong>
                    <em>{item.status}</em>
                    <p>{item.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="funding-grid lower">
          <div className="funding-panel">
            <div className="panel-title">
              <BriefcaseBusiness size={19} aria-hidden="true" />
              <h3>本周 Top Deals</h3>
            </div>
            {snapshot.topDeals.length > 0 ? (
              <div className="deal-list">
                {snapshot.topDeals.map((deal) => (
                  <a
                    className="deal-row"
                    href={deal.sourceUrl}
                    target="_blank"
                    rel="noreferrer"
                    key={`${deal.company}-${deal.eventDate}`}
                  >
                    <span>{deal.country}</span>
                    <strong>{deal.company}</strong>
                    <em>{deal.round || '未标注轮次'}</em>
                    <b>{formatUsd(deal.amountUsd)}</b>
                    <ArrowUpRight size={16} aria-hidden="true" />
                  </a>
                ))}
              </div>
            ) : (
              <div className="funding-empty">
                <FileClock size={24} aria-hidden="true" />
                <p>本周还没有确认事件进入公开统计。</p>
              </div>
            )}
          </div>

          <div className="funding-panel">
            <div className="panel-title">
              <TrendingUp size={19} aria-hidden="true" />
              <h3>重点赛道</h3>
            </div>
            <div className="sector-grid">
              {fundingRadar.sectors.map((sector) => {
                const current = snapshot.sectorBreakdown.find((item) => item.label === sector.id);
                return (
                  <div className="sector-row" key={sector.id} style={{ '--sector': sector.accent }}>
                    <span>{sector.label}</span>
                    <strong>{current?.events || 0}</strong>
                    <em>{formatUsd(current?.amountUsd || 0)}</em>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function SectionHeading({ kicker, title, copy }) {
  return (
    <div className="section-heading">
      <p>{kicker}</p>
      <h2>{title}</h2>
      <span>{copy}</span>
    </div>
  );
}

function ProjectCard({ project }) {
  function handleMove(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width - 0.5) * 10;
    const y = ((event.clientY - rect.top) / rect.height - 0.5) * -10;
    event.currentTarget.style.setProperty('--tilt-x', `${y}deg`);
    event.currentTarget.style.setProperty('--tilt-y', `${x}deg`);
  }

  function resetTilt(event) {
    event.currentTarget.style.setProperty('--tilt-x', '0deg');
    event.currentTarget.style.setProperty('--tilt-y', '0deg');
  }

  return (
    <article
      className="project-card"
      id={project.id}
      style={{ '--accent': project.accent }}
      onMouseMove={handleMove}
      onMouseLeave={resetTilt}
    >
      <ProjectPreview project={project} />

      <div className="card-topline">
        <span className="type-chip">
          <Layers3 size={14} aria-hidden="true" />
          {project.type}
        </span>
        <span className="status-chip">{project.status}</span>
      </div>

      <div className="project-title-row">
        <div>
          <h3>{project.name}</h3>
        </div>
        <span className="launch-icon" aria-hidden="true">
          <ArrowUpRight size={20} />
        </span>
      </div>

      <p className="problem-line">
        <strong>解决的问题：</strong>
        {project.problem}
      </p>
      <p className="project-summary">{project.summary}</p>
      <p className="project-details">{project.details}</p>
      <p className="project-tech">
        <strong>背后做法：</strong>
        {project.techIntro}
      </p>

      <div className="tag-row" aria-label={`${project.name} 项目特点`}>
        {project.tags.map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>

      <div className="card-footer">
        <span className="date-line">
          <CalendarDays size={15} aria-hidden="true" />
          {formatDate(project.publishedAt)}
        </span>
        <div className="card-actions">
          <a
            className="text-icon-link"
            href={project.repoUrl}
            target="_blank"
            rel="noreferrer"
            title="打开代码项目"
            aria-label="打开代码项目"
          >
            <Code2 size={17} aria-hidden="true" />
            看代码
          </a>
          {project.liveUrl ? (
            <a
              className="text-icon-link primary-link"
              href={project.liveUrl}
              target="_blank"
              rel="noreferrer"
              title="打开可以直接使用的页面"
              aria-label="打开可以直接使用的页面"
            >
              <ExternalLink size={17} aria-hidden="true" />
              直接使用
            </a>
          ) : (
            <span
              className="text-icon-link disabled"
              title="这个项目暂时没有可以直接使用的页面"
              aria-disabled="true"
            >
              <ExternalLink size={17} aria-hidden="true" />
              暂未开放
            </span>
          )}
        </div>
      </div>
    </article>
  );
}

function ProjectPreview({ project }) {
  if (project.cover) {
    return (
      <div className="project-preview project-cover" aria-label={`${project.name} 界面预览`}>
        <img src={project.cover} alt={project.coverAlt || `${project.name} 界面封面`} />
      </div>
    );
  }

  return (
    <div className="project-preview preview-render" aria-label={`${project.name} 规划预览`}>
      <div className="render-board">
        <span>{project.preview?.subtitle || project.type}</span>
        <strong>{project.preview?.title || project.name}</strong>
        <div className="render-items">
          {(project.preview?.items || project.tags).slice(0, 4).map((item, index) => (
            <em key={item}>
              <span>{String(index + 1).padStart(2, '0')}</span>
              {item}
            </em>
          ))}
        </div>
      </div>
    </div>
  );
}

function RepositoryRow({ repo }) {
  return (
    <a
      className={repo.highlighted ? 'repo-row highlighted' : 'repo-row'}
      href={repo.repoUrl}
      target="_blank"
      rel="noreferrer"
      aria-label={`打开 ${repo.name} 项目入口`}
    >
      <span className="repo-kind">
        {repo.kind.includes('参考') ? (
          <GitFork size={15} aria-hidden="true" />
        ) : (
          <BookOpen size={15} aria-hidden="true" />
        )}
        {repo.kind}
      </span>
      <span className="repo-row-main">
        <strong>{repo.name}</strong>
        <span>{repo.description}</span>
      </span>
      <span className="repo-row-meta">
        <span>{repo.language || '未标注'}</span>
        <span>{formatDate(repo.updatedAt)}</span>
      </span>
      <ArrowUpRight size={18} aria-hidden="true" />
    </a>
  );
}

export default App;
