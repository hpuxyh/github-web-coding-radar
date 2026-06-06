# 我的项目合集

这是一个项目展示页，用来把我做过的项目集中放在一起。

每个重点项目会说明三件事：

- 它是做什么的。
- 它解决什么问题。
- 可以点哪里直接使用，或者点哪里查看代码。

页面分成三块：

- 融资周报：中美 AI 硬件/机器人投融资雷达。
- 先看这些项目：适合对外介绍的重点项目。
- 全部项目入口：更多公开项目、参考资料和早期练习。
- 更新顺序：按时间看看最近先做了什么。

整理日期：2026-06-06。

## 怎么运行

第一次打开前安装依赖：

```bash
npm install
```

本地预览：

```bash
npm run dev
```

打包发布前检查：

```bash
npm run build
```

## 融资周报怎么维护

这个项目里已经放了一个轻量周报管线：

```text
公开新闻候选 -> 人工确认融资事件 -> 生成周报快照 -> 静态网站展示
```

常用命令：

```bash
npm run funding:candidates
npm run funding:build
npm run build
```

数据入口：

```text
data/funding/manual_events.csv
data/funding/watchlist.json
data/funding/candidate_queries.json
src/data/fundingWeeklySnapshot.js
```

维护方式：

- 先运行 `npm run funding:candidates` 抓取公开候选新闻。
- 人工确认后，把真实融资事件写入 `data/funding/manual_events.csv`，并把 `include_in_report` 填成 `true`。
- 再运行 `npm run funding:build`，脚本会更新前端读取的周报快照。
- 当前公开页面只统计确认事件，候选新闻不会直接进入金额和事件数。

自动化已经放在 `.github/workflows/funding-weekly.yml`：每周一北京时间 09:00 抓候选、生成快照并构建。公开发布时，可以把仓库接到 Cloudflare Pages，构建命令填 `npm run build`，输出目录填 `dist`。

## 怎么更新内容

主要改这个文件：

```text
src/data/projects.js
```

常改的地方：

- `profile`：页面顶部的介绍。
- `projects`：重点项目卡片。
- `repoCatalog`：更多项目入口。

写项目介绍时尽量少用技术词，优先回答：这个东西能帮用户做什么。
