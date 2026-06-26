import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import github_xhs_daily as daily


class GithubXhsDailyTests(unittest.TestCase):
    def ranked_repo(self, name, sources, scores=None, features=None, age_days=10):
        score_values = {
            "hot": 100,
            "used": 100,
            "starred": 100,
            "discussion": 100,
            "frontier": 100,
            "product": 100,
            "rising": 100,
            "all_time": 100,
        }
        score_values.update(scores or {})
        return {
            "full_name": name,
            "name": name.split("/")[-1],
            "html_url": f"https://github.com/{name}",
            "sources": sources,
            "scores": score_values,
            "features": features or [],
            "lens": {},
            "age_days": age_days,
            "stars": 100,
            "forks": 10,
        }

    def test_render_query_expands_relative_dates(self):
        run_date = dt.date(2026, 6, 5)
        query = daily.render_query("created:>={date_365} pushed:>={date_7}", run_date)
        self.assertEqual(query, "created:>=2025-06-05 pushed:>=2026-05-29")

    def test_collect_repositories_respects_min_stars(self):
        class FakeClient:
            def search_repositories(self, query, per_page=50, pages=1):
                return [
                    {
                        "id": 1,
                        "full_name": "demo/under-threshold",
                        "name": "under-threshold",
                        "owner": {"login": "demo"},
                        "html_url": "https://github.com/demo/under-threshold",
                        "stargazers_count": 99,
                        "forks_count": 1,
                        "watchers_count": 99,
                        "open_issues_count": 0,
                        "topics": [],
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-02T00:00:00Z",
                        "pushed_at": "2026-01-02T00:00:00Z",
                    },
                    {
                        "id": 2,
                        "full_name": "demo/qualified",
                        "name": "qualified",
                        "owner": {"login": "demo"},
                        "html_url": "https://github.com/demo/qualified",
                        "stargazers_count": 100,
                        "forks_count": 1,
                        "watchers_count": 100,
                        "open_issues_count": 0,
                        "topics": [],
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-02T00:00:00Z",
                        "pushed_at": "2026-01-02T00:00:00Z",
                    },
                ]

        repos = daily.collect_repositories(
            FakeClient(),
            {
                "per_page": 10,
                "pages": 1,
                "min_stars": 100,
                "all_time_queries": ["created:>={date_365} stars:>=100"],
                "rising_queries": [],
                "frontier_queries": [],
                "product_queries": [],
                "expert_sources": {"enabled": False},
            },
            dt.date(2026, 6, 5),
        )

        self.assertEqual([repo["full_name"] for repo in repos], ["demo/qualified"])

    def test_infer_features_from_description_and_topics(self):
        repo = {
            "full_name": "demo/web-agent",
            "description": "A browser IDE with AI coding agent and live preview",
            "readme_excerpt": "",
            "topics": ["web-ide"],
        }
        features = daily.infer_features(repo)
        self.assertIn("AI Coding / Agent", features)
        self.assertIn("Web IDE / Browser Editor", features)
        self.assertIn("Sandbox / Preview", features)

    def test_first_readme_excerpt_skips_language_nav_noise(self):
        readme = """
# Career-Ops

English | Español | Français | Português (Brasil) | 한국어 | 日本語 | 简体中文

[![stars](https://img.shields.io/github/stars/demo/project)](https://github.com/demo/project)

## What Is This

Career-Ops turns any AI coding CLI into a full job search command center.
Instead of manually tracking applications in a spreadsheet, you get an AI-powered pipeline.
"""
        excerpt = daily.first_readme_excerpt(readme, 260)

        self.assertNotIn("English | Español", excerpt)
        self.assertNotIn("shields.io", excerpt)
        self.assertIn("Career-Ops turns any AI coding CLI", excerpt)

    def test_career_ops_summary_uses_readme_meaning(self):
        repo = {
            "full_name": "santifer/career-ops",
            "name": "career-ops",
            "description": "AI-powered job search system built on Claude Code. 14 skill modes, Go dashboard, PDF generation, batch processing.",
            "readme_excerpt": (
                "Career-Ops turns any AI coding CLI into a full job search command center. "
                "Instead of manually tracking applications in a spreadsheet, you get an AI-powered pipeline."
            ),
            "topics": ["job-search", "resume", "career"],
            "examples": [{"title": "Usage", "body": "/career-ops pdf", "code": ""}],
        }

        summary = daily.summarize_repo_docs_zh(repo)

        self.assertIn("AI 求职指挥中心", summary)
        self.assertIn("主要给", summary)
        self.assertIn("它解决的是", summary)
        self.assertIn("省掉", summary)
        self.assertIn("740+", summary)
        self.assertIn("100+", summary)
        self.assertIn("评估岗位", summary)
        self.assertIn("简历/CV", summary)
        self.assertNotIn("数据应用", summary)

    def test_curated_readme_summaries_prevent_generic_misclassification(self):
        cases = {
            "omnigent-ai/omnigent": ("智能体编排框架", "终端里的 AI 编程助手"),
            "palmier-io/palmier-pro": ("macOS 视频编辑器", "AI 工作流自动化工具"),
            "lintsinghua/claude-code-book": ("架构图", "AI 编程技能/规则包"),
            "HKUDS/Vibe-Trading": ("交易智能体", "HTML 页面生成工具"),
            "browser-use/browser-harness": ("真实浏览器", "终端里的 AI 编程助手"),
        }

        for full_name, (expected, forbidden) in cases.items():
            with self.subTest(full_name=full_name):
                summary = daily.summarize_repo_docs_zh(
                    {
                        "full_name": full_name,
                        "name": full_name.split("/")[-1],
                        "description": "",
                        "readme_excerpt": "",
                        "topics": [],
                        "examples": [],
                    }
                )
                self.assertIn(expected, summary)
                self.assertIn("它解决的是", summary)
                self.assertIn("省掉", summary)
                self.assertNotIn(forbidden, summary)

    def test_curated_readme_summary_table_has_no_known_template_phrases(self):
        overrides = daily.readme_summary_overrides()
        self.assertGreaterEqual(len(overrides), 80)
        forbidden_phrases = [
            "这个项目还没有整理成小白版说明",
            "先点开仓库再人工判断",
            "终端里的 AI 编程助手，主要给习惯",
            "AI 工作流自动化工具，主要给想把 AI 接进业务流程",
            "HTML 页面生成工具，主要给要快速产出网页",
        ]
        for full_name, summary in overrides.items():
            with self.subTest(full_name=full_name):
                for phrase in forbidden_phrases:
                    self.assertNotIn(phrase, summary)

    def test_quantitative_evidence_translates_token_savings(self):
        text = (
            "High-performance CLI proxy that reduces LLM token consumption by 60-90% "
            "on common dev commands. Single Rust binary, 100+ supported commands, <10ms overhead."
        )

        evidence = daily.quantitative_evidence_text(text)

        self.assertIn("常见开发命令可减少 60-90% 的模型 token 消耗", evidence)
        self.assertIn("100+ 个支持命令", evidence)
        self.assertNotIn("on common dev commands", evidence)

    def test_quantitative_evidence_translates_design_counts(self):
        text = "259+ Skills · 142+ Design Systems · Web, desktop and mobile prototypes."

        evidence = daily.quantitative_evidence_text(text)

        self.assertIn("259+ 个技能、142+ 套设计系统", evidence)
        self.assertNotIn("Design Systems", evidence)

    def test_design_project_beats_generic_coding_agent_classification(self):
        repo = {
            "full_name": "demo/open-design",
            "name": "open-design",
            "description": "Claude Code / Codex design workspace for prototypes, slides, images and design systems.",
            "readme_excerpt": "Go from a vague idea to discovering references, editing interactively and producing web, desktop and mobile prototypes.",
            "topics": ["ai-design", "coding-agents", "design-tools"],
            "examples": [{"title": "Demo", "body": "Entry view and mobile onboarding", "code": ""}],
        }

        summary = daily.summarize_repo_docs_zh(repo)

        self.assertIn("设计/原型生成工具", summary)
        self.assertIn("省掉的是先写需求", summary)
        self.assertNotIn("终端里的 AI 编程助手", summary)

    def test_select_rankings_keeps_tabs_exclusive(self):
        shared = self.ranked_repo(
            "demo/shared",
            ["frontier", "product", "rising", "all_time"],
            scores={"hot": 500, "used": 500, "starred": 500, "discussion": 500},
            features=["AI Coding / Agent", "Web IDE / Browser Editor"],
        )
        repos = [
            shared,
            self.ranked_repo("demo/hot", ["rising"], scores={"hot": 400}, features=["AI Coding / Agent"]),
            self.ranked_repo("demo/used", ["product"], scores={"used": 400}, features=["Web IDE / Browser Editor"]),
            self.ranked_repo("demo/starred", ["all_time"], scores={"starred": 400}),
            self.ranked_repo("demo/discussion", ["frontier"], scores={"discussion": 400}),
        ]
        hot, used, starred, discussion, _ = daily.select_rankings(
            repos,
            {
                "hot_limit": 3,
                "used_limit": 3,
                "starred_limit": 3,
                "discussion_limit": 3,
                "xhs_count": 3,
            },
        )
        sections = [hot, used, discussion, starred]
        names = [repo["full_name"] for section in sections for repo in section]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("demo/shared", [repo["full_name"] for repo in hot])
        self.assertNotIn("demo/shared", [repo["full_name"] for repo in used + discussion + starred])

    def test_extract_readme_examples_from_usage_section(self):
        readme = """
# Demo Project

Some intro text.

## Quick start

![Preview screen](docs/preview-screen.png)

Run this command to create your first app:

```bash
npx demo create my-app
cd my-app
```

Open the preview and change the prompt.

### Advanced options

Only read this when you need custom settings.

## License

MIT
"""
        examples = daily.extract_readme_examples(
            readme,
            full_name="demo/project",
            default_branch="main",
        )
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]["title"], "Quick start")
        self.assertIn("create your first app", examples[0]["body"])
        self.assertNotIn("Advanced options", examples[0]["body"])
        self.assertIn("npx demo create my-app", examples[0]["code"])
        self.assertEqual(examples[0]["images"][0]["alt"], "Preview screen")
        self.assertEqual(
            examples[0]["images"][0]["url"],
            "https://raw.githubusercontent.com/demo/project/main/docs/preview-screen.png",
        )
        self.assertEqual(examples[0]["source"], "README")

    def test_extract_repo_full_names_from_public_text(self):
        text = "看这个 https://github.com/openai/codex 和另一个 vercel/ai 都很适合观察。"
        names = daily.extract_repo_full_names_from_text(text)
        self.assertIn("openai/codex", names)
        self.assertIn("vercel/ai", names)

    def test_collect_expert_repositories_from_starred_and_refs(self):
        class FakeClient:
            def list_starred_repositories(self, username, per_page=30, pages=1):
                self.starred_args = (username, per_page, pages)
                return [
                    {
                        "starred_at": "2026-06-05T00:00:00Z",
                        "repo": {
                            "id": 1,
                            "full_name": "demo/starred",
                            "name": "starred",
                            "owner": {"login": "demo"},
                            "html_url": "https://github.com/demo/starred",
                            "description": "AI coding agent",
                            "stargazers_count": 120,
                            "forks_count": 12,
                            "watchers_count": 120,
                            "open_issues_count": 1,
                            "topics": ["ai-coding"],
                            "default_branch": "main",
                        },
                    }
                ]

            def get_repository(self, full_name):
                if full_name != "demo/referenced":
                    return None
                return {
                    "id": 2,
                    "full_name": "demo/referenced",
                    "name": "referenced",
                    "owner": {"login": "demo"},
                    "html_url": "https://github.com/demo/referenced",
                    "description": "Browser IDE",
                    "stargazers_count": 80,
                    "forks_count": 8,
                    "watchers_count": 80,
                    "open_issues_count": 0,
                    "topics": ["web-ide"],
                    "default_branch": "main",
                }

        config = {
            "expert_sources": {
                "enabled": True,
                "starred_per_page": 10,
                "starred_pages": 1,
                "experts": [
                    {
                        "id": "expert",
                        "name": "Expert",
                        "category": "ai_engineer",
                        "github": "expert-user",
                        "track_starred": True,
                        "project_refs": [{"repo": "demo/referenced", "url": "https://github.com/demo/referenced"}],
                    }
                ],
            }
        }

        repos = daily.collect_expert_repositories(FakeClient(), config)
        by_name = {repo["full_name"]: repo for repo in repos}
        self.assertEqual(set(by_name), {"demo/starred", "demo/referenced"})
        self.assertEqual(by_name["demo/starred"]["expert_signals"][0]["source"], "github_star")
        self.assertEqual(by_name["demo/referenced"]["expert_signals"][0]["source"], "project_reference")

    def test_expert_signal_boosts_frontier_score(self):
        run_date = dt.date(2026, 6, 5)
        base_repo = {
            "full_name": "demo/repo",
            "stars": 100,
            "forks": 10,
            "open_issues": 1,
            "created_at": "2026-05-01T00:00:00Z",
            "pushed_at": "2026-06-04T00:00:00Z",
            "features": ["AI Coding / Agent"],
            "expert_signals": [],
        }
        expert_repo = dict(base_repo)
        expert_repo["expert_signals"] = []
        daily.attach_expert_signal(
            expert_repo,
            {
                "expert_id": "expert",
                "expert_name": "Expert",
                "category": "ai_engineer",
                "source": "github_star",
                "repo": "demo/repo",
                "weight": 1.5,
            },
        )

        daily.score_repo(base_repo, {"repos": {}}, run_date)
        daily.score_repo(expert_repo, {"repos": {}}, run_date)
        self.assertGreater(expert_repo["scores"]["hot"], base_repo["scores"]["hot"])
        self.assertGreater(expert_repo["scores"]["frontier"], base_repo["scores"]["frontier"])
        self.assertIn("expert_summary", expert_repo["lens"])

    def test_score_repo_uses_history_delta(self):
        run_date = dt.date(2026, 6, 5)
        history = {
            "repos": {
                "demo/repo": [
                    {
                        "date": "2026-06-03",
                        "stars": 100,
                        "forks": 10,
                        "open_issues": 1,
                    }
                ]
            }
        }
        repo = {
            "full_name": "demo/repo",
            "stars": 150,
            "forks": 12,
            "open_issues": 1,
            "created_at": "2026-05-01T00:00:00Z",
            "pushed_at": "2026-06-04T00:00:00Z",
            "features": ["AI Coding / Agent"],
        }
        daily.score_repo(repo, history, run_date)
        self.assertEqual(repo["delta_stars"], 50)
        self.assertEqual(repo["delta_days"], 2)
        self.assertEqual(repo["delta_per_day"], 25.0)
        self.assertGreater(repo["scores"]["hot"], 0)
        self.assertGreater(repo["scores"]["used"], 0)
        self.assertGreater(repo["scores"]["starred"], 0)
        self.assertGreater(repo["scores"]["discussion"], 0)
        self.assertGreater(repo["scores"]["rising"], 0)
        self.assertGreater(repo["scores"]["frontier"], 0)
        self.assertGreater(repo["scores"]["product"], 0)

    def test_restore_previous_readme_assets_preserves_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            latest_path = Path(tmpdir) / "latest.json"
            latest_path.write_text(
                json.dumps(
                    {
                        "all_repos": [
                            {
                                "full_name": "demo/project",
                                "readme_excerpt": "AI coding agent creates videos from HTML.",
                                "examples": [
                                    {
                                        "title": "Quick start",
                                        "body": "",
                                        "code": "",
                                        "images": [
                                            {
                                                "url": "https://raw.githubusercontent.com/demo/project/main/hero.png",
                                                "alt": "Hero screenshot",
                                            }
                                        ],
                                        "source": "README",
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            repo = {
                "full_name": "demo/project",
                "description": "",
                "readme_excerpt": "",
                "examples": [],
                "topics": [],
                "features": [],
                "stars": 100,
                "forks": 10,
                "open_issues": 1,
                "created_at": "2026-05-01T00:00:00Z",
                "pushed_at": "2026-06-04T00:00:00Z",
                "expert_signals": [],
            }

            assets = daily.load_previous_readme_assets(latest_path)
            restored = daily.restore_previous_readme_assets([repo], assets, {"repos": {}}, dt.date(2026, 6, 5))

        self.assertEqual(restored, 1)
        self.assertEqual(repo["readme_excerpt"], "AI coding agent creates videos from HTML.")
        self.assertEqual(repo["examples"][0]["images"][0]["alt"], "Hero screenshot")
        self.assertIn("AI Coding / Agent", repo["features"])
        self.assertGreater(repo["scores"]["hot"], 0)
        self.assertGreater(repo["scores"]["frontier"], 0)

    def test_embed_radar_payload_escapes_script_end(self):
        html = (
            '<html><script id="embedded-radar-data" type="application/json">'
            '{"date":"old"}'
            '</script></html>'
        )
        payload = {
            "date": "2026-06-22",
            "all_repos": [
                {
                    "full_name": "demo/project",
                    "description": "safe </script><div>& text",
                }
            ],
        }
        updated = daily.embed_radar_payload(html, payload)

        self.assertIn("\\u003c/script\\u003e", updated)
        self.assertNotIn("safe </script><div>& text", updated)
        extracted = daily.extract_embedded_radar_payload_from_text(updated)
        self.assertEqual(extracted, payload)

    def test_readme_image_url_helpers(self):
        self.assertTrue(daily.is_local_readme_image_url("assets/readme-images/demo.png"))
        self.assertTrue(daily.is_local_readme_image_url("/assets/readme-images/demo.png"))
        self.assertFalse(daily.is_local_readme_image_url("https://raw.githubusercontent.com/demo/repo/main/demo.png"))
        self.assertEqual(
            daily.image_extension_from_url("https://raw.githubusercontent.com/demo/repo/main/demo.PNG?raw=1"),
            ".png",
        )
        self.assertEqual(
            daily.image_extension_from_url("https://raw.githubusercontent.com/demo/repo/main/demo.jpeg"),
            ".jpeg",
        )
        self.assertEqual(
            daily.normalize_readme_image_url(
                "https://raw.githubusercontent.com/demo/repo/main/demo.png%23gh-light-mode-only"
            ),
            "https://raw.githubusercontent.com/demo/repo/main/demo.png",
        )
        self.assertEqual(
            daily.image_extension_from_url(
                "https://raw.githubusercontent.com/demo/repo/main/demo.png%23gh-light-mode-only"
            ),
            ".png",
        )
        self.assertEqual(daily.image_extension_from_url("https://github.com/user-attachments/assets/demo"), "")

    def test_readme_image_content_type_helpers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            headers_path = Path(tmpdir) / "headers"
            headers_path.write_text("HTTP/2 200\ncontent-type: text/html; charset=utf-8\n", encoding="utf-8")
            self.assertEqual(daily.image_content_type_from_headers(headers_path), "text/html")
            self.assertEqual(daily.image_extension_from_headers(headers_path), "")

            headers_path.write_text("HTTP/2 200\ncontent-type: image/webp\n", encoding="utf-8")
            self.assertEqual(daily.image_content_type_from_headers(headers_path), "image/webp")
            self.assertEqual(daily.image_extension_from_headers(headers_path), ".webp")

    def test_localize_payload_images_removes_failed_external_images(self):
        payload = {
            "frontier": [
                {
                    "full_name": "demo/project",
                    "examples": [
                        {
                            "images": [
                                {"url": "https://example.com/good.png", "alt": "good"},
                                {"url": "https://example.com/bad.png", "alt": "bad"},
                                {"url": "assets/readme-images/existing.webp", "alt": "existing"},
                            ]
                        }
                    ],
                }
            ]
        }
        original_download = daily.download_readme_image

        def fake_download(url, asset_dir=daily.LOCAL_README_IMAGE_DIR):
            return "assets/readme-images/good.webp" if "good" in url else None

        daily.download_readme_image = fake_download
        try:
            localized = daily.localize_payload_images(payload)
        finally:
            daily.download_readme_image = original_download

        images = payload["frontier"][0]["examples"][0]["images"]
        self.assertEqual(localized, 1)
        self.assertEqual(
            [image["url"] for image in images],
            ["assets/readme-images/good.webp", "assets/readme-images/existing.webp"],
        )
        self.assertEqual(images[0]["source_url"], "https://example.com/good.png")

    def test_bootstrap_history_from_embedded_payload(self):
        history = {"repos": {}}
        payload = {
            "date": "2026-06-21",
            "all_repos": [
                {
                    "full_name": "demo/project",
                    "stars": "123",
                    "forks": 4,
                    "open_issues": None,
                }
            ],
        }

        added = daily.bootstrap_history_from_payload(history, payload)
        self.assertEqual(added, 1)
        self.assertEqual(history["repos"]["demo/project"][0]["date"], "2026-06-21")
        self.assertEqual(history["repos"]["demo/project"][0]["stars"], 123)
        self.assertEqual(history["repos"]["demo/project"][0]["open_issues"], 0)

    def test_build_markdown_contains_required_sections(self):
        run_date = dt.date(2026, 6, 5)
        repo = {
            "full_name": "demo/repo",
            "name": "repo",
            "html_url": "https://github.com/demo/repo",
            "stars": 1000,
            "forks": 100,
            "created_at": "2026-05-01T00:00:00Z",
            "pushed_at": "2026-06-04T00:00:00Z",
            "language": "TypeScript",
            "license": "MIT",
            "features": ["AI Coding / Agent"],
            "description": "AI coding tool",
            "readme_excerpt": "",
            "age_days": 35,
            "star_velocity": 28.57,
            "delta_stars": None,
            "delta_days": None,
            "delta_per_day": 0,
            "topics": ["ai-coding"],
        }
        markdown = daily.build_markdown(run_date, [repo], [repo], [repo], [repo], [repo], {"per_page": 40, "pages": 1})
        self.assertIn("热度榜", markdown)
        self.assertIn("大家都在用榜", markdown)
        self.assertIn("高收藏榜", markdown)
        self.assertIn("参与讨论榜", markdown)
        self.assertIn("小红书草稿", markdown)
        self.assertIn("demo/repo", markdown)


if __name__ == "__main__":
    unittest.main()
