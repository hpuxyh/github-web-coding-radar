#!/usr/bin/env python3
"""Build daily crawler-based AI frontier rankings and Xiaohongshu drafts."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import http.client
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


API_ROOT = "https://api.github.com"
USER_AGENT = "github-xhs-daily/0.1"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "github_xhs_config.json"


FEATURE_RULES = [
    (
        "AI Coding / Agent",
        [
            "ai coding",
            "coding agent",
            "agentic",
            "code agent",
            "copilot",
            "llm",
            "large language model",
            "code generation",
            "generate code",
            "vibe coding",
        ],
    ),
    (
        "Web IDE / Browser Editor",
        [
            "web ide",
            "browser ide",
            "online ide",
            "monaco",
            "code editor",
            "vscode",
            "vs code",
            "stackblitz",
            "playground",
        ],
    ),
    (
        "Sandbox / Preview",
        [
            "sandbox",
            "container",
            "preview",
            "live preview",
            "runtime",
            "terminal",
            "execute code",
            "code execution",
        ],
    ),
    (
        "MCP / Tool Calling",
        [
            "mcp",
            "model context protocol",
            "tool calling",
            "function calling",
            "tools",
            "agent tools",
        ],
    ),
    (
        "Low-code / No-code",
        [
            "low-code",
            "low code",
            "no-code",
            "no code",
            "visual builder",
            "app builder",
            "drag and drop",
        ],
    ),
    (
        "Deploy / Cloud",
        [
            "deploy",
            "deployment",
            "cloud",
            "serverless",
            "hosting",
            "edge",
        ],
    ),
    (
        "Collaboration",
        [
            "collaboration",
            "collaborative",
            "multiplayer",
            "real-time",
            "realtime",
            "pair programming",
        ],
    ),
    (
        "Testing / Quality",
        [
            "test",
            "testing",
            "lint",
            "review",
            "debug",
            "debugger",
            "observability",
        ],
    ),
]


FRONTIER_KEYWORDS = [
    "agent",
    "agentic",
    "coding agent",
    "mcp",
    "model context protocol",
    "claude code",
    "cursor",
    "codex",
    "deepseek",
    "reasoning",
    "eval",
    "benchmark",
    "context",
    "memory",
    "tool calling",
    "code review",
    "observability",
    "token",
    "sandbox",
    "terminal",
    "developer-tools",
]


PRODUCT_KEYWORDS = [
    "app",
    "web app",
    "prototype",
    "builder",
    "editor",
    "dashboard",
    "template",
    "workflow",
    "html",
    "design",
    "xhs",
    "wechat",
    "notion",
    "obsidian",
    "browser",
    "capture",
    "preview",
    "one-click",
    "visual",
    "product",
]


FEATURE_LABEL_ZH = {
    "AI Coding / Agent": "人工智能编程 / 智能体",
    "Web IDE / Browser Editor": "网页集成开发环境 / 浏览器编辑器",
    "Sandbox / Preview": "沙盒 / 预览",
    "MCP / Tool Calling": "模型上下文协议 / 工具调用",
    "Low-code / No-code": "低代码 / 无代码",
    "Deploy / Cloud": "部署 / 云服务",
    "Collaboration": "协作",
    "Testing / Quality": "测试 / 质量",
}

EXPERT_CATEGORY_LABEL_ZH = {
    "ai_engineer": "AI 工程师",
    "open_source_author": "开源作者",
    "investor_product_expert": "投资人 / 产品专家",
}

EXPERT_SIGNAL_LABEL_ZH = {
    "github_star": "GitHub 公开收藏",
    "tweet_link": "公开推文 / 帖子",
    "project_reference": "项目引用",
}

DEFAULT_EXPERT_SOURCE_WEIGHTS = {
    "github_star": 1.0,
    "tweet_link": 1.2,
    "project_reference": 1.1,
}

DEFAULT_EXPERT_CATEGORY_WEIGHTS = {
    "ai_engineer": 1.35,
    "open_source_author": 1.25,
    "investor_product_expert": 1.1,
}

GITHUB_REPO_URL_RE = re.compile(
    r"github\.com[/:](?P<owner>[A-Za-z0-9-]+)/(?P<repo>[A-Za-z0-9_.-]+)",
    re.I,
)


@dataclass(frozen=True)
class RunPaths:
    data_path: Path
    output_dir: Path


class GithubApiError(RuntimeError):
    pass


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        request_interval: float = 0.0,
        timeout_seconds: float = 60.0,
        retries: int = 2,
    ):
        self.token = token
        self.request_interval = max(0.0, request_interval)
        self.timeout_seconds = max(1.0, timeout_seconds)
        self.retries = max(0, retries)
        self._last_request_at = 0.0

    def request_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        accept: str = "application/vnd.github+json",
    ) -> Any:
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{API_ROOT}{path}?{query}"
        else:
            url = f"{API_ROOT}{path}"

        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)

        headers = {
            "Accept": accept,
            "Accept-Encoding": "identity",
            "Connection": "close",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                cmd = [
                    "curl",
                    "--http1.1",
                    "-L",
                    "-sS",
                    "--retry",
                    str(self.retries),
                    "--retry-all-errors",
                    "--connect-timeout",
                    str(min(20.0, self.timeout_seconds)),
                    "--max-time",
                    str(self.timeout_seconds),
                    "-w",
                    "\n%{http_code}",
                ]
                for key, value in headers.items():
                    cmd.extend(["-H", f"{key}: {value}"])
                cmd.append(url)
                completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
                self._last_request_at = time.monotonic()
                if completed.returncode != 0:
                    raise urllib.error.URLError(completed.stderr.strip() or f"curl exit {completed.returncode}")
                body, status_text = completed.stdout.rsplit("\n", 1)
                status = int(status_text)
                if status >= 400:
                    reset_text = ""
                    message = f"GitHub API error {status} for {url}: {body[:500]}{reset_text}"
                    if status not in {429, 500, 502, 503, 504} or attempt >= self.retries:
                        raise GithubApiError(message)
                    last_error = GithubApiError(message)
                else:
                    try:
                        return json.loads(body)
                    except json.JSONDecodeError as exc:
                        last_error = exc
                        if attempt >= self.retries:
                            raise GithubApiError(f"Invalid JSON response for {url}: {exc}") from exc
            except urllib.error.HTTPError as exc:
                self._last_request_at = time.monotonic()
                body = exc.read().decode("utf-8", errors="replace")
                reset_at = exc.headers.get("X-RateLimit-Reset")
                reset_text = ""
                if reset_at and reset_at.isdigit():
                    reset_dt = dt.datetime.fromtimestamp(int(reset_at))
                    reset_text = f" Reset time: {reset_dt.isoformat()}."
                message = f"GitHub API error {exc.code} for {url}: {body[:500]}{reset_text}"
                if exc.code not in {429, 500, 502, 503, 504} or attempt >= self.retries:
                    raise GithubApiError(message) from exc
                last_error = GithubApiError(message)
            except (urllib.error.URLError, TimeoutError, socket.timeout, http.client.IncompleteRead) as exc:
                self._last_request_at = time.monotonic()
                last_error = exc
                if attempt >= self.retries:
                    raise GithubApiError(f"Network error for {url}: {exc}") from exc

            backoff = min(2 ** attempt * 3, 20)
            time.sleep(backoff)

        raise GithubApiError(f"Network error for {url}: {last_error}")

    def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 50,
        pages: int = 1,
    ) -> list[dict[str, Any]]:
        repos: list[dict[str, Any]] = []
        for page in range(1, pages + 1):
            result = self.request_json(
                "/search/repositories",
                {
                    "q": query,
                    "sort": sort,
                    "order": order,
                    "per_page": per_page,
                    "page": page,
                },
            )
            repos.extend(result.get("items", []))
        return repos

    def get_repository(self, full_name: str) -> dict[str, Any] | None:
        encoded_name = urllib.parse.quote(full_name, safe="/")
        try:
            return self.request_json(f"/repos/{encoded_name}")
        except GithubApiError:
            return None

    def list_starred_repositories(
        self,
        username: str,
        per_page: int = 30,
        pages: int = 1,
    ) -> list[dict[str, Any]]:
        encoded_user = urllib.parse.quote(username, safe="")
        starred: list[dict[str, Any]] = []
        for page in range(1, pages + 1):
            data = self.request_json(
                f"/users/{encoded_user}/starred",
                {"per_page": per_page, "page": page},
                accept="application/vnd.github.star+json",
            )
            if not isinstance(data, list):
                continue
            starred.extend(data)
        return starred

    def get_readme_text(self, full_name: str) -> str | None:
        encoded_name = urllib.parse.quote(full_name, safe="/")
        try:
            data = self.request_json(f"/repos/{encoded_name}/readme")
        except GithubApiError:
            return None

        content = data.get("content")
        encoding = data.get("encoding")
        if content and encoding == "base64":
            try:
                raw = base64.b64decode(content).decode("utf-8", errors="replace")
                return raw
            except (ValueError, UnicodeError):
                return None
        return None


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve_path(value: str | None, default: str) -> Path:
    path = Path(value or default)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def today_in_timezone(tz_name: str) -> dt.date:
    try:
        from zoneinfo import ZoneInfo

        return dt.datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        return dt.date.today()


def parse_iso_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def days_between(run_date: dt.date, iso_datetime: str | None) -> int:
    parsed = parse_iso_datetime(iso_datetime)
    if not parsed:
        return 9999
    return max(0, (run_date - parsed.date()).days)


def format_date(run_date: dt.date, days_back: int) -> str:
    return (run_date - dt.timedelta(days=days_back)).isoformat()


def render_query(template: str, run_date: dt.date) -> str:
    context = {
        "today": run_date.isoformat(),
        "yesterday": format_date(run_date, 1),
        "date_7": format_date(run_date, 7),
        "date_14": format_date(run_date, 14),
        "date_30": format_date(run_date, 30),
        "date_60": format_date(run_date, 60),
        "date_90": format_date(run_date, 90),
        "date_180": format_date(run_date, 180),
        "date_365": format_date(run_date, 365),
    }
    return template.format(**context)


def is_probable_full_name(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$", value.strip()))


def normalize_full_name(value: str) -> str:
    owner, repo = value.strip().strip("/").split("/", 1)
    repo = repo.removesuffix(".git")
    return f"{owner}/{repo}"


def extract_repo_full_names_from_text(value: str | None) -> list[str]:
    if not value:
        return []

    names: list[str] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        if not is_probable_full_name(candidate):
            return
        full_name = normalize_full_name(candidate)
        repo_name = full_name.split("/", 1)[1].lower()
        if repo_name in {
            "settings",
            "topics",
            "collections",
            "explore",
            "marketplace",
            "search",
            "login",
            "signup",
        }:
            return
        if full_name not in seen:
            seen.add(full_name)
            names.append(full_name)

    for match in GITHUB_REPO_URL_RE.finditer(value):
        add(f"{match.group('owner')}/{match.group('repo')}")

    for token in re.findall(r"(?<![@\w.-])([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?![\w.-])", value):
        add(token)

    return names


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def expert_category_label(category: str) -> str:
    return EXPERT_CATEGORY_LABEL_ZH.get(category, category or "未分类专家")


def expert_signal_label(source: str) -> str:
    return EXPERT_SIGNAL_LABEL_ZH.get(source, source or "专家信号")


def expert_source_weight(config: dict[str, Any], source: str) -> float:
    weights = config.get("weights") or {}
    return float(weights.get(source, DEFAULT_EXPERT_SOURCE_WEIGHTS.get(source, 1.0)))


def expert_category_weight(config: dict[str, Any], category: str) -> float:
    weights = config.get("category_weights") or {}
    return float(weights.get(category, DEFAULT_EXPERT_CATEGORY_WEIGHTS.get(category, 1.0)))


def expert_total_weight(config: dict[str, Any], expert: dict[str, Any], source: str) -> float:
    category = str(expert.get("category") or "")
    base = float(expert.get("weight", 1.0))
    return round(
        base * expert_category_weight(config, category) * expert_source_weight(config, source),
        3,
    )


def signal_key(signal: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(signal.get("expert_id") or ""),
        str(signal.get("source") or ""),
        str(signal.get("repo") or ""),
        str(signal.get("url") or ""),
    )


def attach_expert_signal(repo: dict[str, Any], signal: dict[str, Any]) -> None:
    signal.setdefault("category_label", expert_category_label(str(signal.get("category") or "")))
    signal.setdefault("source_label", expert_signal_label(str(signal.get("source") or "")))
    signal["weight"] = float(signal.get("weight") or 1.0)
    signals = repo.setdefault("expert_signals", [])
    if signal_key(signal) not in {signal_key(item) for item in signals}:
        signals.append(signal)
    repo["expert_score"] = round(sum(float(item.get("weight") or 0) for item in signals), 3)


def compact_int(value: int | float | None) -> str:
    if value is None:
        return "0"
    value = float(value)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(int(value))


def clean_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_readme_excerpt(text: str | None, max_chars: int) -> str:
    if not text:
        return ""
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("#", "-", "*", ">")):
            line = line.lstrip("#-* >").strip()
        if line.lower().startswith(("badge", "license", "sponsor")):
            continue
        line = clean_markdown(line)
        if line:
            lines.append(line)
        if sum(len(item) for item in lines) >= max_chars:
            break
    excerpt = " ".join(lines)
    return excerpt[:max_chars].strip()


EXAMPLE_HEADING_KEYWORDS = [
    "quick start",
    "quickstart",
    "getting started",
    "usage",
    "example",
    "examples",
    "demo",
    "try it",
    "how to use",
    "run",
    "快速开始",
    "开始使用",
    "使用方法",
    "用法",
    "示例",
    "例子",
    "演示",
]


def heading_parts(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.strip())
    if not match:
        return None
    title = clean_markdown(match.group(2)).strip()
    return len(match.group(1)), title


def looks_like_example_heading(title: str) -> bool:
    normalized = title.lower()
    return any(keyword in normalized for keyword in EXAMPLE_HEADING_KEYWORDS)


def clean_example_text(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[-*+]\s+", "", line)
    line = re.sub(r"^\d+[.)]\s+", "", line)
    line = clean_markdown(line)
    return line.strip()


def image_alt_from_html_img(tag: str) -> str:
    match = re.search(r"\balt=[\"']([^\"']*)[\"']", tag, re.I)
    return clean_markdown(match.group(1)).strip() if match else ""


def image_url_from_html_img(tag: str) -> str:
    match = re.search(r"\bsrc=[\"']([^\"']+)[\"']", tag, re.I)
    return match.group(1).strip() if match else ""


def normalize_image_url(raw_url: str, full_name: str, default_branch: str) -> str:
    url = raw_url.strip().strip("<>").strip("'\"")
    if not url or url.startswith(("#", "mailto:", "data:")):
        return ""
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith(("http://", "https://")):
        return url.replace("/blob/", "/raw/")
    if not full_name:
        return ""

    path = url.lstrip("/")
    if path.startswith("./"):
        path = path[2:]
    quoted_path = urllib.parse.quote(path, safe="/:%?&=+.-_~")
    return f"https://raw.githubusercontent.com/{full_name}/{default_branch or 'main'}/{quoted_path}"


def looks_like_useful_image(url: str, alt: str) -> bool:
    haystack = f"{url} {alt}".lower()
    if any(skip in haystack for skip in ["badge", "shields.io", "codecov", "license", "npm version"]):
        return False
    if re.search(r"\.(png|jpe?g|gif|webp|avif|svg)(?:[?#].*)?$", url, re.I):
        return True
    return any(host in url for host in ["github.com/user-attachments/assets/", "githubusercontent.com"])


def extract_images_from_lines(
    lines: list[str], full_name: str, default_branch: str, limit: int = 2
) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    seen: set[str] = set()

    for raw_line in lines:
        for alt, raw_url in re.findall(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", raw_line):
            url = normalize_image_url(raw_url, full_name, default_branch)
            clean_alt = clean_markdown(alt).strip()
            if url and url not in seen and looks_like_useful_image(url, clean_alt):
                images.append({"url": url, "alt": clean_alt or "项目示例图"})
                seen.add(url)
            if len(images) >= limit:
                return images

        for tag in re.findall(r"<img\b[^>]*>", raw_line, re.I):
            raw_url = image_url_from_html_img(tag)
            clean_alt = image_alt_from_html_img(tag)
            url = normalize_image_url(raw_url, full_name, default_branch)
            if url and url not in seen and looks_like_useful_image(url, clean_alt):
                images.append({"url": url, "alt": clean_alt or "项目示例图"})
                seen.add(url)
            if len(images) >= limit:
                return images

    return images


def compact_example_body(lines: list[str], max_chars: int = 260) -> str:
    cleaned: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("```"):
            continue
        if heading_parts(line):
            continue
        if re.search(r"!\[[^\]]*\]\([^)]+\)|<img|badge|shields|\.svg|\.png|\.gif", line, re.I):
            continue
        text = clean_example_text(line)
        if text:
            cleaned.append(text)
        if sum(len(item) for item in cleaned) >= max_chars:
            break
    body = " ".join(cleaned)
    return body[:max_chars].strip()


def extract_first_code_block(lines: list[str], max_chars: int = 360) -> str:
    in_block = False
    code_lines: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            if in_block and code_lines:
                break
            in_block = not in_block
            continue
        if in_block:
            if line.strip():
                code_lines.append(line)
            if sum(len(item) for item in code_lines) >= max_chars:
                break
    code = "\n".join(code_lines).strip()
    return code[:max_chars].strip()


def extract_readme_examples(
    text: str | None, full_name: str = "", default_branch: str = "main", limit: int = 2
) -> list[dict[str, Any]]:
    if not text:
        return []

    lines = text.splitlines()
    examples: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        heading = heading_parts(line)
        if not heading:
            continue
        level, title = heading
        if level == 1:
            continue
        if not looks_like_example_heading(title):
            continue

        section_lines: list[str] = []
        for following in lines[index + 1 :]:
            next_heading = heading_parts(following)
            if next_heading and next_heading[0] <= level:
                break
            section_lines.append(following)
            if len(section_lines) >= 36:
                break

        body = compact_example_body(section_lines)
        code = extract_first_code_block(section_lines)
        images = extract_images_from_lines(section_lines, full_name, default_branch)
        if not body and not code and not images:
            continue

        examples.append(
            {
                "title": title[:60],
                "body": body,
                "code": code,
                "images": images,
                "source": "README",
            }
        )
        if len(examples) >= limit:
            break

    fallback_images = extract_images_from_lines(lines[:120], full_name, default_branch)
    if examples and fallback_images and not any(example.get("images") for example in examples):
        examples[0]["images"] = fallback_images
    elif not examples and fallback_images:
        examples.append(
            {
                "title": "项目截图 / 演示图",
                "body": "README 里提供的项目截图，先看图大致了解它实际长什么样。",
                "code": "",
                "images": fallback_images,
                "source": "README",
            }
        )

    return examples


def normalize_repo(item: dict[str, Any], source: str, query: str) -> dict[str, Any]:
    owner = item.get("owner") or {}
    license_info = item.get("license") or {}
    return {
        "id": item.get("id"),
        "full_name": item.get("full_name"),
        "name": item.get("name"),
        "owner": owner.get("login"),
        "html_url": item.get("html_url"),
        "default_branch": item.get("default_branch") or "main",
        "description": item.get("description") or "",
        "language": item.get("language"),
        "stars": int(item.get("stargazers_count") or 0),
        "forks": int(item.get("forks_count") or 0),
        "watchers": int(item.get("watchers_count") or 0),
        "open_issues": int(item.get("open_issues_count") or 0),
        "topics": item.get("topics") or [],
        "homepage": item.get("homepage") or "",
        "license": license_info.get("spdx_id") if license_info else None,
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "pushed_at": item.get("pushed_at"),
        "sources": [source],
        "queries": [query],
        "readme_excerpt": "",
        "examples": [],
        "features": [],
        "expert_signals": [],
        "expert_score": 0.0,
        "scores": {},
        "notes": [],
    }


def merge_repo(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    existing["sources"] = sorted(set(existing.get("sources", [])) | set(incoming["sources"]))
    existing["queries"] = sorted(set(existing.get("queries", [])) | set(incoming["queries"]))
    for field in [
        "description",
        "language",
        "stars",
        "forks",
        "watchers",
        "open_issues",
        "topics",
        "homepage",
        "license",
        "updated_at",
        "pushed_at",
    ]:
        if incoming.get(field):
            existing[field] = incoming[field]
    for signal in incoming.get("expert_signals") or []:
        attach_expert_signal(existing, signal)
    return existing


def infer_features(repo: dict[str, Any]) -> list[str]:
    text_parts = [
        repo.get("full_name") or "",
        repo.get("description") or "",
        repo.get("readme_excerpt") or "",
        " ".join(repo.get("topics") or []),
    ]
    haystack = " ".join(text_parts).lower()
    features: list[str] = []
    for label, keywords in FEATURE_RULES:
        if any(keyword in haystack for keyword in keywords):
            features.append(label)
    return features[:5]


def text_haystack(repo: dict[str, Any]) -> str:
    return " ".join(
        [
            repo.get("full_name") or "",
            repo.get("description") or "",
            repo.get("readme_excerpt") or "",
            " ".join(repo.get("topics") or []),
            " ".join(repo.get("features") or []),
        ]
    ).lower()


def keyword_hits(repo: dict[str, Any], keywords: list[str]) -> list[str]:
    haystack = text_haystack(repo)
    return [keyword for keyword in keywords if keyword in haystack]


def feature_labels_zh(features: list[str]) -> list[str]:
    return [FEATURE_LABEL_ZH.get(feature, feature) for feature in features]


def expert_signal_summary(repo: dict[str, Any], limit: int = 3) -> str:
    signals = repo.get("expert_signals") or []
    if not signals:
        return ""

    experts: list[str] = []
    categories: list[str] = []
    sources: list[str] = []
    for signal in signals:
        expert = str(signal.get("expert_name") or signal.get("expert_id") or "").strip()
        category = str(signal.get("category_label") or expert_category_label(signal.get("category") or "")).strip()
        source = str(signal.get("source_label") or expert_signal_label(signal.get("source") or "")).strip()
        if expert and expert not in experts:
            experts.append(expert)
        if category and category not in categories:
            categories.append(category)
        if source and source not in sources:
            sources.append(source)

    expert_text = "、".join(experts[:limit])
    if len(experts) > limit:
        expert_text += f" 等 {len(experts)} 个观察源"
    category_text = "、".join(categories[:2])
    source_text = "、".join(sources[:2])
    return f"{expert_text} 通过{source_text}关注到它，覆盖{category_text}。"


def expert_score_components(repo: dict[str, Any]) -> tuple[float, int, int]:
    signals = repo.get("expert_signals") or []
    if not signals:
        return 0.0, 0, 0
    expert_ids = {str(signal.get("expert_id") or signal.get("expert_name") or "") for signal in signals}
    categories = {str(signal.get("category") or "") for signal in signals}
    score = sum(float(signal.get("weight") or 0) for signal in signals)
    return score, len([item for item in expert_ids if item]), len([item for item in categories if item])


def editorial_lens(repo: dict[str, Any]) -> dict[str, Any]:
    frontier_hits = keyword_hits(repo, FRONTIER_KEYWORDS)
    product_hits = keyword_hits(repo, PRODUCT_KEYWORDS)
    features = feature_labels_zh(repo.get("features") or [])
    expert_summary = expert_signal_summary(repo)
    front_signal = "、".join(features[:2]) if features else "开发者关注度"
    product_signal = "、".join(product_hits[:3]) if product_hits else front_signal
    frontier_reason = f"命中 {front_signal}，适合观察前沿团队正在围绕哪些工具链和能力下注。"
    product_reason = f"命中 {product_signal}，适合拆成可使用、可演示、可复刻的产品点子。"
    if expert_summary:
        frontier_reason = f"{expert_summary}再叠加 {front_signal} 信号，适合优先观察。"
        product_reason = f"{expert_summary}如果它能落到具体使用场景，也值得拆成产品点子。"
    return {
        "frontier_hits": frontier_hits[:8],
        "product_hits": product_hits[:8],
        "expert_summary": expert_summary,
        "frontier_reason": frontier_reason,
        "product_reason": product_reason,
    }


def load_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"repos": {}}
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("repos", {})
    return data


def latest_snapshot_before(
    history: dict[str, Any], full_name: str, run_date: dt.date
) -> dict[str, Any] | None:
    snapshots = history.get("repos", {}).get(full_name, [])
    prior = [
        snapshot
        for snapshot in snapshots
        if snapshot.get("date") and dt.date.fromisoformat(snapshot["date"]) < run_date
    ]
    if not prior:
        return None
    return max(prior, key=lambda item: item["date"])


def score_repo(repo: dict[str, Any], history: dict[str, Any], run_date: dt.date) -> None:
    stars = repo["stars"]
    forks = repo["forks"]
    age_days = max(1, days_between(run_date, repo.get("created_at")))
    pushed_age = max(0, days_between(run_date, repo.get("pushed_at")))
    features = repo.get("features") or []
    feature_bonus = len(features) * 12
    star_velocity = stars / age_days

    prior = latest_snapshot_before(history, repo["full_name"], run_date)
    delta_stars = None
    delta_days = None
    delta_per_day = 0.0
    if prior:
        prior_date = dt.date.fromisoformat(prior["date"])
        delta_days = max(1, (run_date - prior_date).days)
        delta_stars = max(0, stars - int(prior.get("stars", 0)))
        delta_per_day = delta_stars / delta_days

    freshness = 45 / (1 + pushed_age)
    young_bonus = 80 if age_days <= 30 else 45 if age_days <= 90 else 20 if age_days <= 180 else 0
    lens = editorial_lens(repo)
    frontier_signal = min(len(lens["frontier_hits"]) * 28, 180)
    product_signal = min(len(lens["product_hits"]) * 24, 170)
    total_star_weight = min(math.log10(max(stars, 1)) * 35, 190)
    velocity_weight = min(star_velocity * 14, 240) + min(delta_per_day * 38, 380)
    expert_raw_score, expert_count, expert_category_count = expert_score_components(repo)
    expert_signal_weight = (
        min(expert_raw_score * 36, 260)
        + min(expert_count * 32, 160)
        + min(expert_category_count * 24, 80)
    )

    rising_score = (
        min(star_velocity * 18, 260)
        + min(delta_per_day * 42, 420)
        + min(math.sqrt(max(forks, 0)) * 3, 80)
        + freshness
        + young_bonus
        + feature_bonus
        + expert_signal_weight * 0.35
    )
    all_time_score = stars + forks * 1.5 + feature_bonus * 20 + freshness
    frontier_score = (
        velocity_weight
        + total_star_weight
        + min(math.sqrt(max(forks, 0)) * 4, 100)
        + freshness
        + frontier_signal
        + min(feature_bonus * 1.4, 90)
        + expert_signal_weight
    )
    product_score = (
        min(star_velocity * 16, 240)
        + min(delta_per_day * 36, 360)
        + total_star_weight * 0.65
        + freshness
        + young_bonus
        + product_signal
        + min(feature_bonus * 1.2, 85)
        + expert_signal_weight * 0.55
    )

    repo["age_days"] = age_days
    repo["star_velocity"] = round(star_velocity, 2)
    repo["delta_stars"] = delta_stars
    repo["delta_days"] = delta_days
    repo["delta_per_day"] = round(delta_per_day, 2)
    repo["expert_score"] = round(expert_raw_score, 3)
    repo["scores"] = {
        "all_time": round(all_time_score, 2),
        "rising": round(rising_score, 2),
        "frontier": round(frontier_score, 2),
        "product": round(product_score, 2),
    }
    repo["lens"] = lens


def update_history(path: Path, history: dict[str, Any], repos: list[dict[str, Any]], run_date: dt.date) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    all_repos = history.setdefault("repos", {})
    date_key = run_date.isoformat()
    for repo in repos:
        snapshots = all_repos.setdefault(repo["full_name"], [])
        snapshot = {
            "date": date_key,
            "stars": repo["stars"],
            "forks": repo["forks"],
            "open_issues": repo["open_issues"],
            "pushed_at": repo.get("pushed_at"),
        }
        snapshots = [item for item in snapshots if item.get("date") != date_key]
        snapshots.append(snapshot)
        snapshots.sort(key=lambda item: item["date"])
        all_repos[repo["full_name"]] = snapshots[-120:]

    payload = {
        "updated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "repos": all_repos,
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def chinese_intro(repo: dict[str, Any]) -> str:
    description = repo.get("description") or ""
    excerpt = repo.get("readme_excerpt") or ""
    if description:
        return description.strip()
    if excerpt:
        return excerpt[:150].strip()
    return "这个项目暂时没有清晰的简介，需要点开 README 再做人工补充。"


def xhs_angle(repo: dict[str, Any]) -> str:
    features = repo.get("features") or []
    if "AI Coding / Agent" in features:
        return "人工智能编程工作流"
    if "Web IDE / Browser Editor" in features:
        return "浏览器里写代码"
    if "Sandbox / Preview" in features:
        return "在线运行和预览代码"
    if "MCP / Tool Calling" in features:
        return "让模型连接工具和上下文"
    if "Low-code / No-code" in features:
        return "可视化搭应用"
    return "开发者效率工具"


def repo_card(repo: dict[str, Any], index: int, list_name: str) -> str:
    features = feature_labels_zh(repo.get("features") or []) or ["待人工确认"]
    delta = "暂无历史快照"
    if repo.get("delta_stars") is not None:
        delta = f"{repo['delta_days']} 天涨星 {repo['delta_stars']}，约 {repo['delta_per_day']}/天"
    topics = ", ".join(repo.get("topics")[:8]) if repo.get("topics") else "无"
    lens = repo.get("lens") or {}
    reason = lens.get("product_reason") if list_name == "产品点子榜" else lens.get("frontier_reason")
    reason = reason or "适合作为选题池里的候选项目继续观察。"
    expert_line = ""
    expert_summary = expert_signal_summary(repo)
    if expert_summary:
        expert_line = f"- 人物/专家信号：{expert_summary}"
    lines = [
        f"### {index}. {repo['full_name']}",
        f"- 榜单：{list_name}",
        f"- 链接：{repo['html_url']}",
        f"- 数据：{compact_int(repo['stars'])} 个星标，{compact_int(repo['forks'])} 个分支，创建 {repo.get('created_at', '')[:10]}，最近更新 {repo.get('pushed_at', '')[:10]}",
        f"- 语言/协议：{repo.get('language') or '未知'} / {repo.get('license') or '未知'}",
        f"- 网页编程功能：{', '.join(features)}",
        f"- 项目介绍：{chinese_intro(repo)}",
        expert_line,
        f"- 选题判断：{reason}",
        f"- 热度信号：项目年龄 {repo.get('age_days')} 天，平均 {repo.get('star_velocity')}/天；{delta}",
        f"- Topics：{topics}",
    ]
    return "\n".join(line for line in lines if line)


def xhs_draft(repo: dict[str, Any], index: int) -> str:
    features = feature_labels_zh(repo.get("features") or []) or ["开发者效率"]
    feature_lines = "\n".join(f"- {feature}" for feature in features[:4])
    intro = chinese_intro(repo)
    angle = xhs_angle(repo)
    delta_text = ""
    if repo.get("delta_stars") is not None:
        delta_text = f"，最近 {repo['delta_days']} 天新增 {repo['delta_stars']} 个星标"
    title = f"{repo['name']}：一个值得关注的 {angle} 开源项目"
    cover = f"{repo['name']}｜{angle}"
    body = f"""#### 草稿 {index}: {title}

封面文案：{cover}

开头：
今天刷到一个 GitHub 项目 {repo['full_name']}，适合关注网页编程 / 人工智能编程的朋友收藏。

项目是做什么的：
{intro}

核心功能：
{feature_lines}

为什么现在值得看：
目前 {compact_int(repo['stars'])} 个星标，创建于 {repo.get('created_at', '')[:10]}，最近仍有更新{delta_text}。如果你在做在线集成开发环境、人工智能写代码、代码运行沙盒或开发者工具，可以重点看它的产品思路和说明文档表达。

可展开讲的角度：
- 它解决了网页编程里的哪个具体痛点
- 它和传统本地集成开发环境 / 普通代码生成工具有什么不同
- 哪个功能最适合做成小红书截图或录屏演示

项目链接：
{repo['html_url']}

标签：
#GitHub #开源项目 #网页编程 #人工智能编程 #程序员工具 #开发者工具"""
    return body


def build_markdown(
    run_date: dt.date,
    frontier: list[dict[str, Any]],
    product_ideas: list[dict[str, Any]],
    all_time: list[dict[str, Any]],
    rising: list[dict[str, Any]],
    xhs_repos: list[dict[str, Any]],
    config: dict[str, Any],
) -> str:
    generated_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    lines = [
        f"# GitHub 网页编程日报 - {run_date.isoformat()}",
        "",
        f"生成时间：{generated_at}",
        "",
        "## 今日摘要",
        "",
        f"- 前沿关注榜收录 {len(frontier)} 个项目，用来观察人工智能前沿团队和技术专家可能关注的工具链方向。",
        f"- 产品点子榜收录 {len(product_ideas)} 个项目，用来观察网页编程用户正在做出哪些有意思、实用、可复刻的产品。",
        f"- 历史高星榜收录 {len(all_time)} 个项目，按星标、分支、网页编程相关功能和近期活跃度排序。",
        f"- 新项目潜力榜收录 {len(rising)} 个项目，按创建时间、星标密度、更新活跃度、功能匹配度和历史快照涨星排序。",
        "- 第一次运行时没有历史涨星数据；连续运行后，“最近涨星”会越来越准。",
        "",
        "## 前沿关注榜",
        "",
    ]

    if frontier:
        for index, repo in enumerate(frontier, 1):
            lines.append(repo_card(repo, index, "前沿关注榜"))
            lines.append("")
    else:
        lines.extend(["没有拿到符合默认前沿关注查询的项目。", ""])

    lines.extend(["## 产品点子榜", ""])
    if product_ideas:
        for index, repo in enumerate(product_ideas, 1):
            lines.append(repo_card(repo, index, "产品点子榜"))
            lines.append("")
    else:
        lines.extend(["没有拿到符合默认产品点子查询的项目。", ""])

    lines.extend(
        [
        "## 历史高星榜",
        "",
        ]
    )

    if all_time:
        for index, repo in enumerate(all_time, 1):
            lines.append(repo_card(repo, index, "历史高星榜"))
            lines.append("")
    else:
        lines.extend(["没有拿到历史高星项目。", ""])

    lines.extend(["## 新项目潜力榜", ""])
    if rising:
        for index, repo in enumerate(rising, 1):
            lines.append(repo_card(repo, index, "新项目潜力榜"))
            lines.append("")
    else:
        lines.extend(["没有拿到符合默认网页编程查询的新项目。可以在 config 里放宽星标或关键词。", ""])

    lines.extend(["## 小红书草稿", ""])
    if xhs_repos:
        for index, repo in enumerate(xhs_repos, 1):
            lines.append(xhs_draft(repo, index))
            lines.append("")
    else:
        lines.extend(["没有可生成草稿的项目。", ""])

    lines.extend(
        [
            "## 数据口径",
            "",
            f"- GitHub 搜索每个查询最多抓取 {config.get('per_page', 50)} 条，默认只抓第 {config.get('pages', 1)} 页。",
            "- 人物/专家观察源：只读取公开 GitHub star、配置里的公开推文链接和项目引用，不采集私信、私有收藏或登录后内容。",
            "- 前沿关注榜：优先看智能体、模型上下文协议、代码智能体、开发者工具链、评测、上下文记忆等信号。",
            "- 产品点子榜：优先看应用、编辑器、模板、原型、仪表盘、可视化工作流、浏览器工具等信号。",
            "- 历史高星榜：GitHub 搜索按星标排序后，再用本地评分做二次排序。",
            "- 新项目潜力榜：优先搜索最近创建项目；如果已有历史快照，会加入真实涨星速度。",
            "- 说明文档摘要为程序自动抽取，发布前建议人工补一遍中文表达和截图。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def summarize_expert_sources(repos: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    signals = [signal for repo in repos for signal in repo.get("expert_signals") or []]
    experts = sorted({str(signal.get("expert_id") or signal.get("expert_name") or "") for signal in signals if signal})
    categories = sorted({str(signal.get("category_label") or "") for signal in signals if signal.get("category_label")})
    source_types = sorted({str(signal.get("source_label") or "") for signal in signals if signal.get("source_label")})
    return {
        "enabled": bool((config.get("expert_sources") or {}).get("enabled", False)),
        "configured_experts": len(iter_enabled_experts(config)),
        "matched_repositories": len([repo for repo in repos if repo.get("expert_signals")]),
        "signal_count": len(signals),
        "expert_count": len([item for item in experts if item]),
        "categories": categories,
        "source_types": source_types,
    }


def write_outputs(
    paths: RunPaths,
    run_date: dt.date,
    all_repos: list[dict[str, Any]],
    frontier: list[dict[str, Any]],
    product_ideas: list[dict[str, Any]],
    all_time: list[dict[str, Any]],
    rising: list[dict[str, Any]],
    xhs_repos: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[Path, Path]:
    day_dir = paths.output_dir / run_date.isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)

    markdown = build_markdown(run_date, frontier, product_ideas, all_time, rising, xhs_repos, config)
    markdown_path = day_dir / "github-web-coding-daily.md"
    json_path = day_dir / "repos.json"
    markdown_path.write_text(markdown, encoding="utf-8")
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "date": run_date.isoformat(),
                "frontier": frontier,
                "product_ideas": product_ideas,
                "all_time": all_time,
                "rising": rising,
                "xhs_repos": xhs_repos,
                "all_repos": all_repos,
                "expert_sources": summarize_expert_sources(all_repos, config),
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )

    paths.output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(markdown_path, paths.output_dir / "latest.md")
    shutil.copyfile(json_path, paths.output_dir / "latest.json")
    return markdown_path, json_path


def iter_enabled_experts(config: dict[str, Any]) -> list[dict[str, Any]]:
    expert_config = config.get("expert_sources") or {}
    if not expert_config.get("enabled", False):
        return []
    experts = []
    for expert in expert_config.get("experts") or []:
        if expert.get("enabled", True):
            experts.append(expert)
    return experts


def expert_display_name(expert: dict[str, Any]) -> str:
    return str(expert.get("name") or expert.get("github") or expert.get("id") or "未命名观察源")


def expert_id(expert: dict[str, Any]) -> str:
    return str(expert.get("id") or expert.get("github") or expert_display_name(expert)).strip()


def base_expert_signal(
    expert_config: dict[str, Any],
    expert: dict[str, Any],
    source: str,
    repo_full_name: str,
    url: str = "",
    note: str = "",
    starred_at: str | None = None,
) -> dict[str, Any]:
    category = str(expert.get("category") or "")
    signal = {
        "expert_id": expert_id(expert),
        "expert_name": expert_display_name(expert),
        "category": category,
        "category_label": expert_category_label(category),
        "source": source,
        "source_label": expert_signal_label(source),
        "repo": repo_full_name,
        "url": url,
        "note": note,
        "weight": expert_total_weight(expert_config, expert, source),
    }
    if expert.get("github"):
        signal["github"] = expert.get("github")
    if expert.get("x"):
        signal["x"] = expert.get("x")
    if starred_at:
        signal["starred_at"] = starred_at
    return signal


def reference_entry_parts(entry: Any) -> tuple[list[str], str, str]:
    if isinstance(entry, str):
        return extract_repo_full_names_from_text(entry), entry, ""
    if not isinstance(entry, dict):
        return [], "", ""

    names: list[str] = []
    for key in ["repo", "repos", "full_name", "full_names"]:
        for value in as_list(entry.get(key)):
            if isinstance(value, str):
                names.extend(extract_repo_full_names_from_text(value))

    url = str(entry.get("url") or entry.get("link") or "")
    text = " ".join(str(entry.get(key) or "") for key in ["text", "title", "note", "summary"])
    names.extend(extract_repo_full_names_from_text(f"{url} {text}"))
    note = str(entry.get("note") or entry.get("title") or entry.get("summary") or "").strip()

    unique_names = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)
    return unique_names, url, note


def normalize_starred_item(item: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if isinstance(item.get("repo"), dict):
        return item["repo"], item.get("starred_at")
    return item, item.get("starred_at")


def collect_expert_repositories(
    client: GitHubClient,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    expert_config = config.get("expert_sources") or {}
    experts = iter_enabled_experts(config)
    if not experts:
        return []

    per_page = int(expert_config.get("starred_per_page", expert_config.get("per_page", 20)))
    pages = int(expert_config.get("starred_pages", expert_config.get("pages", 1)))
    merged: dict[str, dict[str, Any]] = {}

    def add_repo(item: dict[str, Any], signal: dict[str, Any], query: str) -> None:
        repo = normalize_repo(item, "expert", query)
        if not repo.get("full_name"):
            return
        signal["repo"] = repo["full_name"]
        attach_expert_signal(repo, signal)
        if repo["full_name"] in merged:
            merge_repo(merged[repo["full_name"]], repo)
        else:
            merged[repo["full_name"]] = repo

    for expert in experts:
        name = expert_display_name(expert)
        expert_name = expert_id(expert)
        if expert.get("track_starred", True) and expert.get("github"):
            try:
                starred_items = client.list_starred_repositories(
                    str(expert["github"]),
                    per_page=per_page,
                    pages=pages,
                )
            except GithubApiError as exc:
                print(f"Expert source skipped for {name}: {exc}", file=sys.stderr)
                starred_items = []

            for item in starred_items:
                repo_item, starred_at = normalize_starred_item(item)
                full_name = repo_item.get("full_name") or ""
                if not full_name:
                    continue
                signal = base_expert_signal(
                    expert_config,
                    expert,
                    "github_star",
                    full_name,
                    url=f"https://github.com/{expert['github']}?tab=stars",
                    note="该观察源的公开 GitHub star 列表出现过这个项目。",
                    starred_at=starred_at,
                )
                add_repo(repo_item, signal, f"expert:{expert_name}:github_star")

        for source, key in [
            ("tweet_link", "tweet_links"),
            ("project_reference", "project_refs"),
        ]:
            for entry in as_list(expert.get(key)):
                repo_names, url, note = reference_entry_parts(entry)
                for full_name in repo_names:
                    item = client.get_repository(full_name)
                    if not item:
                        print(f"Expert reference skipped for {name}: {full_name}", file=sys.stderr)
                        continue
                    signal = base_expert_signal(
                        expert_config,
                        expert,
                        source,
                        full_name,
                        url=url or f"https://github.com/{full_name}",
                        note=note or "公开链接或项目引用里出现过这个仓库。",
                    )
                    add_repo(item, signal, f"expert:{expert_name}:{source}")

    return list(merged.values())


def collect_repositories(
    client: GitHubClient, config: dict[str, Any], run_date: dt.date
) -> list[dict[str, Any]]:
    per_page = int(config.get("per_page", 50))
    pages = int(config.get("pages", 1))
    merged: dict[str, dict[str, Any]] = {}

    for section, queries in [
        ("all_time", config.get("all_time_queries", [])),
        ("rising", config.get("rising_queries", [])),
        ("frontier", config.get("frontier_queries", [])),
        ("product", config.get("product_queries", [])),
    ]:
        for template in queries:
            query = render_query(template, run_date)
            try:
                items = client.search_repositories(query, per_page=per_page, pages=pages)
            except GithubApiError as exc:
                print(f"Search skipped for {section}: {query} ({exc})", file=sys.stderr)
                continue
            for item in items:
                repo = normalize_repo(item, section, query)
                if not repo.get("full_name"):
                    continue
                if repo["full_name"] in merged:
                    merge_repo(merged[repo["full_name"]], repo)
                else:
                    merged[repo["full_name"]] = repo

    for repo in collect_expert_repositories(client, config):
        if not repo.get("full_name"):
            continue
        if repo["full_name"] in merged:
            merge_repo(merged[repo["full_name"]], repo)
        else:
            merged[repo["full_name"]] = repo

    return list(merged.values())


def enrich_repositories(
    client: GitHubClient,
    repos: list[dict[str, Any]],
    config: dict[str, Any],
    history: dict[str, Any],
    run_date: dt.date,
) -> None:
    max_readmes = int(config.get("max_readmes", 12))
    readme_chars = int(config.get("readme_excerpt_chars", 700))
    likely_interesting = sorted(
        repos,
        key=lambda repo: (
            "rising" in repo.get("sources", []),
            repo.get("stars", 0),
            repo.get("forks", 0),
        ),
        reverse=True,
    )
    readme_targets = {repo["full_name"] for repo in likely_interesting[:max_readmes]}

    for repo in repos:
        if repo["full_name"] in readme_targets:
            readme_text = client.get_readme_text(repo["full_name"])
            repo["readme_excerpt"] = first_readme_excerpt(readme_text, readme_chars)
            repo["examples"] = extract_readme_examples(
                readme_text,
                full_name=repo["full_name"],
                default_branch=repo.get("default_branch") or "main",
            )
        repo["features"] = infer_features(repo)
        score_repo(repo, history, run_date)


def select_rankings(
    repos: list[dict[str, Any]], config: dict[str, Any]
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    frontier_limit = int(config.get("frontier_limit", 15))
    product_limit = int(config.get("product_limit", 15))
    top_limit = int(config.get("top_limit", 20))
    rising_limit = int(config.get("rising_limit", 20))
    xhs_count = int(config.get("xhs_count", 5))
    rising_max_age_days = int(config.get("rising_max_age_days", 180))

    # 同一个项目只进一个榜单，避免不同标签页里重复出现。
    # 认领顺序跟页面标签一致：大佬在看 -> 产品灵感 -> 正在变火 -> 经典项目。
    claimed: set[str] = set()

    def take(candidates: list[dict[str, Any]], score_key: str, limit: int) -> list[dict[str, Any]]:
        ranked = sorted(
            (repo for repo in candidates if repo["full_name"] not in claimed),
            key=lambda repo: repo["scores"][score_key],
            reverse=True,
        )[:limit]
        for repo in ranked:
            claimed.add(repo["full_name"])
        return ranked

    frontier_candidates = [
        repo
        for repo in repos
        if "frontier" in repo.get("sources", [])
        or repo.get("expert_signals")
        or repo.get("lens", {}).get("frontier_hits")
        or "AI Coding / Agent" in repo.get("features", [])
        or "MCP / Tool Calling" in repo.get("features", [])
    ]
    frontier = take(frontier_candidates, "frontier", frontier_limit)

    product_candidates = [
        repo
        for repo in repos
        if "product" in repo.get("sources", [])
        or repo.get("lens", {}).get("product_hits")
        or "Web IDE / Browser Editor" in repo.get("features", [])
        or "Low-code / No-code" in repo.get("features", [])
        or "Sandbox / Preview" in repo.get("features", [])
    ]
    product_ideas = take(product_candidates, "product", product_limit)

    rising_candidates = [
        repo
        for repo in repos
        if "rising" in repo.get("sources", []) or repo.get("age_days", 9999) <= rising_max_age_days
    ]
    rising = take(rising_candidates, "rising", rising_limit)

    all_time_candidates = [repo for repo in repos if "all_time" in repo.get("sources", [])]
    if not all_time_candidates:
        all_time_candidates = repos
    all_time = take(all_time_candidates, "all_time", top_limit)

    seen: set[str] = set()
    xhs_repos: list[dict[str, Any]] = []
    for repo in product_ideas + frontier + rising + all_time:
        if repo["full_name"] in seen:
            continue
        seen.add(repo["full_name"])
        xhs_repos.append(repo)
        if len(xhs_repos) >= xhs_count:
            break
    return frontier, product_ideas, all_time, rising, xhs_repos


def run(args: argparse.Namespace) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    config = load_config(Path(args.config).resolve())
    if args.top_limit is not None:
        config["top_limit"] = args.top_limit
    if args.frontier_limit is not None:
        config["frontier_limit"] = args.frontier_limit
    if args.product_limit is not None:
        config["product_limit"] = args.product_limit
    if args.rising_limit is not None:
        config["rising_limit"] = args.rising_limit
    if args.xhs_count is not None:
        config["xhs_count"] = args.xhs_count
    if args.max_readmes is not None:
        config["max_readmes"] = args.max_readmes
    if args.request_interval is not None:
        config["request_interval_seconds"] = args.request_interval
    if args.timeout is not None:
        config["request_timeout_seconds"] = args.timeout
    if args.retries is not None:
        config["retries"] = args.retries

    run_date = dt.date.fromisoformat(args.date) if args.date else today_in_timezone(config.get("timezone", "Asia/Shanghai"))
    paths = RunPaths(
        data_path=resolve_path(config.get("history_path"), "data/repo_history.json"),
        output_dir=resolve_path(config.get("output_dir"), "output"),
    )

    token = os.environ.get("GITHUB_TOKEN") or None
    client = GitHubClient(
        token=token,
        request_interval=float(config.get("request_interval_seconds", 0.0)),
        timeout_seconds=float(config.get("request_timeout_seconds", 60.0)),
        retries=int(config.get("retries", 2)),
    )

    history = load_history(paths.data_path)
    repos = collect_repositories(client, config, run_date)
    enrich_repositories(client, repos, config, history, run_date)
    frontier, product_ideas, all_time, rising, xhs_repos = select_rankings(repos, config)
    update_history(paths.data_path, history, repos, run_date)
    markdown_path, json_path = write_outputs(
        paths, run_date, repos, frontier, product_ideas, all_time, rising, xhs_repos, config
    )

    print(f"Generated: {markdown_path}")
    print(f"JSON: {json_path}")
    print(f"Repos collected: {len(repos)}")
    print(f"Frontier ranking: {len(frontier)}")
    print(f"Product ideas ranking: {len(product_ideas)}")
    print(f"All-time ranking: {len(all_time)}")
    print(f"Rising ranking: {len(rising)}")
    print(f"XHS drafts: {len(xhs_repos)}")
    expert_summary = summarize_expert_sources(repos, config)
    if expert_summary["enabled"]:
        print(
            "Expert signals: "
            f"{expert_summary['signal_count']} signals across "
            f"{expert_summary['matched_repositories']} repos "
            f"from {expert_summary['expert_count']} sources"
        )
    if not token:
        print("Tip: set GITHUB_TOKEN in .env to avoid unauthenticated GitHub rate limits.")
    return 0


def print_queries(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config).resolve())
    run_date = dt.date.fromisoformat(args.date) if args.date else today_in_timezone(config.get("timezone", "Asia/Shanghai"))
    for name in ["all_time_queries", "rising_queries", "frontier_queries", "product_queries"]:
        print(f"[{name}]")
        for template in config.get(name, []):
            print(render_query(template, run_date))
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="每天帮你找好项目：生成 AI 前沿、Web Coding 和热门开源项目榜单。"
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="collect repos and generate the daily report")
    run_parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    run_parser.add_argument("--date", help="run date, YYYY-MM-DD")
    run_parser.add_argument("--top-limit", type=int)
    run_parser.add_argument("--frontier-limit", type=int)
    run_parser.add_argument("--product-limit", type=int)
    run_parser.add_argument("--rising-limit", type=int)
    run_parser.add_argument("--xhs-count", type=int)
    run_parser.add_argument("--max-readmes", type=int)
    run_parser.add_argument("--request-interval", type=float)
    run_parser.add_argument("--timeout", type=float)
    run_parser.add_argument("--retries", type=int)
    run_parser.set_defaults(func=run)

    queries_parser = subparsers.add_parser("queries", help="print rendered GitHub search queries")
    queries_parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    queries_parser.add_argument("--date", help="run date, YYYY-MM-DD")
    queries_parser.set_defaults(func=print_queries)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        args = parser.parse_args(["run"])
    try:
        return args.func(args)
    except GithubApiError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
