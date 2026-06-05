# 每天帮你找 GitHub 好项目

这个工具每天自动从 GitHub 爬取和筛选 AI 前沿、Web Coding 与开发者工具相关项目，生成适合产品经理浏览和小红书选题使用的榜单：

- 历史高星榜：累计 stars 很高、适合长期做选题池的项目。
- 新项目潜力榜：最近创建、正在积累热度、和 Web Coding / AI Coding / Web IDE / MCP 等方向相关的新项目。

它还会生成适合小红书使用的 Markdown 草稿，包含项目介绍、Web Coding 功能点、发布角度、封面文案、标签和项目链接。

## 快速开始

克隆项目后，先进入项目目录：

```bash
git clone <你的仓库地址>
cd github-web-coding-radar
```

建议配置 GitHub token，避免 GitHub 未登录 API 限流：

```bash
cp .env.example .env
# 然后把 .env 里的 GITHUB_TOKEN 改成你的 token
```

生成当天数据：

```bash
python3 scripts/github_xhs_daily.py run
```

生成结果在：

- `output/latest.md`
- `output/latest.json`
- `output/YYYY-MM-DD/github-web-coding-daily.md`
- `output/YYYY-MM-DD/repos.json`

浏览网页：

```bash
make view
```

然后打开：

```text
http://127.0.0.1:8787/viewer.html
```

网页读取的是 `output/latest.json`。如果页面提示找不到数据，先运行一次生成命令。

## 常用命令

查看今天实际会用哪些 GitHub 搜索：

```bash
python3 scripts/github_xhs_daily.py queries
```

只生成少量内容，用来测试：

```bash
python3 scripts/github_xhs_daily.py run --top-limit 5 --rising-limit 5 --xhs-count 3 --max-readmes 5
```

指定日期回放：

```bash
python3 scripts/github_xhs_daily.py run --date 2026-06-05
```

运行测试：

```bash
python3 -m unittest discover -s tests
```

启动浏览页：

```bash
make view
```

## 每日自动运行

macOS 可以用 launchd 安装一个每天运行的计划任务：

```bash
bash scripts/install_daily_launchd.sh
```

默认每天本地时间 08:30 运行。可以用环境变量改时间：

```bash
RUN_HOUR=9 RUN_MINUTE=15 bash scripts/install_daily_launchd.sh
```

日志会写到 `logs/github-xhs-daily.out.log` 和 `logs/github-xhs-daily.err.log`。

## 调整选题方向

编辑 `config/github_xhs_config.json`：

- `all_time_queries`：历史高星榜的 GitHub Search 查询。
- `rising_queries`：新项目潜力榜的 GitHub Search 查询。
- `top_limit`：历史高星榜输出数量。
- `rising_limit`：新项目潜力榜输出数量。
- `xhs_count`：每天生成几篇小红书草稿。
- `request_interval_seconds`：GitHub API 请求间隔。没有 token 时建议保持 6 秒以上。
- `request_timeout_seconds`：单次 GitHub 请求超时时间。
- `retries`：网络抖动或 GitHub 5xx 时的自动重试次数。

查询支持日期占位：

- `{today}`
- `{yesterday}`
- `{date_7}`
- `{date_14}`
- `{date_30}`
- `{date_60}`
- `{date_90}`
- `{date_180}`
- `{date_365}`

例子：

```json
"created:>={date_30} stars:>=10 archived:false vibe-coding"
```

## 排名逻辑

历史高星榜主要看：

- stars
- forks
- 是否命中 Web Coding 功能关键词
- 最近 push 活跃度

新项目潜力榜主要看：

- 创建时间
- stars / 项目年龄
- forks
- 最近 push 活跃度
- 是否命中 Web Coding 功能关键词
- 本地历史快照里的真实涨星速度

第一次运行时还没有历史快照，所以“要火起来”的判断会更像早期雷达。连续跑几天后，`data/repo_history.json` 会记录每天 stars，潜力榜会逐渐加入真实涨星速度。
