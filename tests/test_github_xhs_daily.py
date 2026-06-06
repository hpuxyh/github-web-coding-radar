import datetime as dt
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import github_xhs_daily as daily


class GithubXhsDailyTests(unittest.TestCase):
    def ranked_repo(self, name, sources, scores=None, features=None, age_days=10):
        score_values = {
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
        query = daily.render_query("created:>={date_60} pushed:>={date_7}", run_date)
        self.assertEqual(query, "created:>=2026-04-06 pushed:>=2026-05-29")

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

    def test_select_rankings_keeps_tabs_exclusive(self):
        shared = self.ranked_repo(
            "demo/shared",
            ["frontier", "product", "rising", "all_time"],
            scores={"frontier": 500, "product": 500, "rising": 500, "all_time": 500},
            features=["AI Coding / Agent", "Web IDE / Browser Editor"],
        )
        repos = [
            shared,
            self.ranked_repo("demo/frontier", ["frontier"], scores={"frontier": 400}, features=["AI Coding / Agent"]),
            self.ranked_repo("demo/product", ["product"], scores={"product": 400}, features=["Web IDE / Browser Editor"]),
            self.ranked_repo("demo/rising", ["rising"], scores={"rising": 400}),
            self.ranked_repo("demo/classic", ["all_time"], scores={"all_time": 400}),
        ]
        frontier, product_ideas, all_time, rising, _ = daily.select_rankings(
            repos,
            {
                "frontier_limit": 3,
                "product_limit": 3,
                "top_limit": 3,
                "rising_limit": 3,
                "xhs_count": 3,
            },
        )
        sections = [frontier, product_ideas, rising, all_time]
        names = [repo["full_name"] for section in sections for repo in section]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("demo/shared", [repo["full_name"] for repo in frontier])
        self.assertNotIn("demo/shared", [repo["full_name"] for repo in product_ideas + rising + all_time])

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
        self.assertGreater(repo["scores"]["rising"], 0)
        self.assertGreater(repo["scores"]["frontier"], 0)
        self.assertGreater(repo["scores"]["product"], 0)

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
        self.assertIn("前沿关注榜", markdown)
        self.assertIn("产品点子榜", markdown)
        self.assertIn("历史高星榜", markdown)
        self.assertIn("新项目潜力榜", markdown)
        self.assertIn("小红书草稿", markdown)
        self.assertIn("demo/repo", markdown)


if __name__ == "__main__":
    unittest.main()
