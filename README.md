# 每天帮你找好项目

这个仓库现在有两层用途：

- 项目合集页：把我的重点项目、可使用页面和更多项目入口集中展示。
- 项目雷达工具：每天从公开项目里筛选值得关注的新工具，方便做产品灵感和内容选题。

公开页面会尽量用白话解释每个项目能做什么，少放技术名词。

## 公开页面

本地预览：

```bash
npm install
npm run dev
```

打包发布前检查：

```bash
npm run build
```

发布成公开网页时：

- 构建命令：`npm run build`
- 输出目录：`dist`

## 项目雷达

如果你只是想看当前榜单，不想安装爬虫、配置 token 或运行脚本，可以打开仓库里的 `radar.html`。这是完整静态版，已经内置一份榜单数据。

生成当天数据：

```bash
python3 scripts/github_xhs_daily.py run
```

生成结果在：

- `output/latest.md`
- `output/latest.json`
- `output/YYYY-MM-DD/github-web-coding-daily.md`
- `output/YYYY-MM-DD/repos.json`

本地浏览旧版雷达页：

```bash
make view
```

然后打开：

```text
http://127.0.0.1:8787/viewer.html
```

## 配置项目雷达

编辑 `config/github_xhs_config.json`：

- `all_time_queries`：历史高星榜搜索。
- `rising_queries`：新项目潜力榜搜索。
- `xhs_count`：每天生成几篇小红书草稿。
- `expert_sources`：人物/专家观察源。支持公开 GitHub stars、手工配置的公开推文链接和项目引用。

人物/专家观察源的详细字段、隐私边界、速率限制和评分权重见 [docs/expert-observation-sources.md](docs/expert-observation-sources.md)。

## 更新项目合集

主要改这个文件：

```text
src/data/projects.js
```

写项目介绍时尽量少用技术词，优先回答：这个东西能帮用户做什么。
