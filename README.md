# 把 GitHub 网页模板改成我的作品

这个仓库现在有两层用途：

- 项目合集页：把我的重点项目、可使用页面和更多项目入口集中展示。
- 项目雷达工具：每天从公开项目里筛选值得关注的新工具，方便做产品灵感和内容选题。
- 网页模板改造社区说明：把“找项目”升级成“发现现成网页 + 小白站内编辑 + 作品展示”的产品方向。
- 新手改网页页面：帮普通人从 GitHub 上已经能打开的 HTML 页面开始，直接改成自己的网页作品。

公开页面会尽量用白话解释每个模板能做什么，少放技术名词。

## 新方向：GitHub 网页模板改造社区

新手改网页页面：

```text
https://hpuxyh.github.io/github-web-coding-radar/remix-mvp.html
```

说明页：

```text
https://hpuxyh.github.io/github-web-coding-radar/remix-community.html
```

这个方向的核心不是再做一个 GitHub 排行榜，而是把 GitHub 上已经能打开的网页，变成小白可以直接修改、预览和展示的模板。

- 看不懂 GitHub 项目目录和英文说明。
- 不知道哪个网页能直接打开、适不适合拉进来改。
- 不知道自己应该先换哪些文字、图片、卡片和按钮。
- 改完之后不知道怎么上线、怎么展示。

第一版先做轻社区：

- 先精选适合拉进来的 GitHub HTML 网页模板。
- 每个模板都用白话解释：它长什么样、适合改成什么、哪些地方先不要碰。
- 每个模板给 3 个改法，并让用户先打开示例前端，再点进编辑页直接改内容、看预览、保存到自己的浏览器。
- 用户可以提交自己的改造成品，展示原模板、截图、链接和改造说明。

当前页面已先把这条链路做成可以打开的版本：

- 3 类适合新手的网页模板：个人主页、清单看板、转盘选择小工具。
- 当前 3 个示例会对应真实 GitHub HTML 页面：个人主页 HTML 模板、清单看板 HTML 模板、转盘选择 HTML 小工具。
- 每类作品给 3 个改法：第一步、第二步、以后可以做。
- 每个改法都会告诉用户：要准备什么、先换哪些内容、哪些以后再做、怎么看效果、怎么分享给别人，并提供站内示例前端和直接编辑入口。
- 修改后的内容会先保存在当前浏览器里，用户可以打开“我的前端”查看自己的版本。
- 作品提交先保存在自己的浏览器里，后续再接正式提交和审核。

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
