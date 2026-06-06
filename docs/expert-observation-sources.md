# 人物/专家观察源方案

目标：把榜单从“只靠 GitHub 热度推断”，升级成“真实人物关注 + GitHub 热度验证”。这里的“人物关注”不是替代 GitHub 热度，而是给前沿榜和产品灵感榜增加早期信号。

## 三类观察源

1. AI 工程师
   - 观察重点：正在关注哪些智能体、模型上下文、代码生成、评测、沙盒、工具调用项目。
   - 典型字段：姓名、GitHub 用户名、X 用户名、公开 star、公开提到的项目链接。

2. 开源作者
   - 观察重点：成熟开源作者最近收藏、引用、参与了哪些新工具，尤其是开发者工具和前端生态。
   - 典型字段：姓名、GitHub 用户名、开源方向、公开 star、公开项目引用。

3. 投资人 / 产品专家
   - 观察重点：他们公开讨论的产品机会、工作流变化、可商业化的新工具。
   - 典型字段：姓名、X 用户名、公开推文链接、明确提到的 GitHub 项目、人工备注。

## 第一版数据来源

- GitHub 用户公开 starred 仓库：通过 GitHub API `/users/{username}/starred` 获取。
- 单个项目详情：通过 GitHub API `/repos/{owner}/{repo}` 获取 stars、forks、语言、更新时间等。
- 公开推文 / 帖子链接：先由配置文件人工放入，脚本只从公开链接或备注文本里识别 GitHub 仓库名。
- 项目引用：先由配置文件人工放入，例如 `owner/repo` 或 `https://github.com/owner/repo`。

第一版不抓取登录后的 X 信息，也不读取私信、私有收藏、浏览器历史或任何非公开内容。

## 可采集字段

每条专家信号会写入项目的 `expert_signals`：

```json
{
  "expert_id": "swyx",
  "expert_name": "Swyx",
  "category": "ai_engineer",
  "category_label": "AI 工程师",
  "source": "github_star",
  "source_label": "GitHub 公开收藏",
  "repo": "owner/repo",
  "url": "https://github.com/swyxio?tab=stars",
  "note": "该观察源的公开 GitHub star 列表出现过这个项目。",
  "weight": 1.552,
  "starred_at": "2026-06-06T00:00:00Z"
}
```

不是每个字段都会存在。例如 GitHub API 未返回 `starred_at` 时，这个字段会为空。

## 隐私和速率限制

- 只采公开数据，不采私有 star、私信、登录后内容。
- 默认每个专家只抓 1 页公开 star，每页 20 个项目。
- `request_interval_seconds` 默认 6.5 秒，适合没有 GitHub token 时降低限流风险。
- 单个专家源失败不会中断整天任务，只会跳过并在命令行打印原因。
- 建议配置 `GITHUB_TOKEN`，否则 GitHub 未认证 API 额度较低。

## 专家名单配置格式

位置：`config/github_xhs_config.json` 的 `expert_sources`。

```json
{
  "expert_sources": {
    "enabled": true,
    "starred_per_page": 20,
    "starred_pages": 1,
    "weights": {
      "github_star": 1.0,
      "tweet_link": 1.2,
      "project_reference": 1.1
    },
    "category_weights": {
      "ai_engineer": 1.35,
      "open_source_author": 1.25,
      "investor_product_expert": 1.1
    },
    "experts": [
      {
        "id": "example-person",
        "name": "Example Person",
        "category": "ai_engineer",
        "github": "example",
        "x": "example",
        "weight": 1.1,
        "track_starred": true,
        "tweet_links": [
          {
            "url": "https://x.com/example/status/123",
            "repos": ["owner/repo"],
            "note": "公开帖子里提到这个项目。"
          }
        ],
        "project_refs": [
          {
            "repo": "owner/repo",
            "url": "https://github.com/owner/repo",
            "note": "人工加入的明确项目引用。"
          }
        ]
      }
    ]
  }
}
```

## 采集策略

1. GitHub stars
   - 读取每个专家公开 star 列表。
   - 把返回的仓库标准化成项目对象。
   - 给项目增加一条 `github_star` 专家信号。

2. 推文链接
   - 第一版只支持配置里人工放入公开链接。
   - 如果链接或备注里包含 `github.com/owner/repo` 或 `owner/repo`，脚本会识别项目。
   - 如果只是一条 X 链接，没有项目名，需要在 `repos` 字段手工写明。

3. 项目引用
   - 支持 `repo`、`repos`、`full_name`、`url`、`note`。
   - 脚本会拉取对应 GitHub 仓库详情，再合并进候选池。

## 评分权重

每条专家信号的基础权重：

- GitHub 公开收藏：`1.0`
- 公开推文 / 帖子：`1.2`
- 项目引用：`1.1`

每类观察源的类别权重：

- AI 工程师：`1.35`
- 开源作者：`1.25`
- 投资人 / 产品专家：`1.1`

专家本人还可以配置 `weight`。最终单条信号权重：

```text
专家个人权重 * 类别权重 * 信号来源权重
```

分数接入方式：

- 前沿榜：完整加入专家信号权重。
- 产品灵感榜：加入 55% 专家信号权重。
- 正在变火榜：加入 35% 专家信号权重。
- 经典项目榜：仍主要看 stars 和 forks，不额外放大人物信号。

这样能让“真实人物关注”影响早期发现，但仍需要 GitHub 热度、更新活跃、功能关键词一起验证。

## 已接入位置

- `scripts/github_xhs_daily.py`
  - `GitHubClient.list_starred_repositories`
  - `GitHubClient.get_repository`
  - `collect_expert_repositories`
  - `expert_signals`
  - `score_repo` 专家信号加权
  - `latest.json` 的 `expert_sources` 摘要

- `viewer.html`
  - 顶部增加“人物信号”统计。
  - 项目卡片增加“人物/专家信号”区块。
  - 搜索支持专家姓名、专家类别、信号来源和备注。

## 小步实现计划

第一步，已经完成：

- 配置格式落地。
- GitHub 公开 star 采集落地。
- 手工推文链接和项目引用解析落地。
- 评分和页面展示接入。
- 单元测试覆盖基本解析、信号合并和专家加分。

第二步，建议明天继续：

- 人工精修专家名单，增加 20 到 50 个稳定观察源。
- 给每个专家增加“为什么跟踪他/她”的备注。
- 每天输出“新增被专家关注的项目”小节。
- 把 X/Twitter 链接整理成手工输入表，先不做登录态抓取。

第三步，后续再做：

- 接 X API 或 RSS/Newsletter 源。
- 给专家信号做时间衰减，最近 7 天更高，旧信号逐渐降低。
- 记录专家信号历史，做“今天新出现在哪些专家源里”的差分。
