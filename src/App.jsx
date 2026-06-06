import React, { useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUpRight,
  BookOpen,
  CalendarDays,
  Code2,
  ExternalLink,
  GitFork,
  Github,
  Layers3,
  Rocket,
  Search,
  Sparkles,
} from 'lucide-react';
import { assets, githubSnapshot, profile, projects, repoCatalog } from './data/projects.js';

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
        <a className="scroll-cue" href="#projects" aria-label="跳到项目区">
          <ArrowDown size={18} aria-hidden="true" />
        </a>
      </section>

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
