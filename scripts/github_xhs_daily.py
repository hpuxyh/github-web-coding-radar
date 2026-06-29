#!/usr/bin/env python3
"""Build daily crawler-based AI frontier rankings and Xiaohongshu drafts."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
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
EMBEDDED_RADAR_DATA_RE = re.compile(
    r'(<script id="embedded-radar-data" type="application/json">)(.*?)(</script>)',
    re.S,
)
LOCAL_README_IMAGE_DIR = PROJECT_ROOT / "public" / "assets" / "readme-images"
LOCAL_README_IMAGE_BASE = "assets/readme-images"
IMAGE_CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
}
IMAGE_EXTENSION_FALLBACK_CONTENT_TYPES = {
    "application/octet-stream",
    "binary/octet-stream",
}
IMAGE_FILE_EXTENSIONS = set(IMAGE_CONTENT_TYPE_EXTENSIONS.values()) | {".jpeg"}
OPTIMIZED_README_IMAGE_MAX_WIDTH = 1400
OPTIMIZED_README_IMAGE_QUALITY = 82
OPTIMIZABLE_README_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
GITHUB_README_IMAGE_MODE_SUFFIXES = (
    "%23gh-light-mode-only",
    "%23gh-dark-mode-only",
)
NEW_RANKING_SECTIONS = ("hot", "used", "starred", "discussion")
LEGACY_RANKING_SECTIONS = ("frontier", "product_ideas", "all_time", "rising")
PAYLOAD_REPO_SECTIONS = ("all_repos", *NEW_RANKING_SECTIONS, *LEGACY_RANKING_SECTIONS, "xhs_repos")
PAYLOAD_IMAGE_SECTIONS = (*NEW_RANKING_SECTIONS, *LEGACY_RANKING_SECTIONS, "xhs_repos", "all_repos")


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

README_LANGUAGE_WORDS = {
    "english",
    "español",
    "français",
    "português",
    "한국어",
    "日本語",
    "简体中文",
    "繁體中文",
    "русский",
    "polski",
    "العربية",
    "deutsch",
    "tiếng việt",
    "ไทย",
}

README_SUMMARY_OVERRIDES = {
    "santifer/career-ops": (
        "Career-Ops 是一个 AI 求职指挥中心，主要给正在找工作、需要大量筛选职位和定制投递材料的候选人用。"
        "它解决的是手动评估岗位、改简历/CV、写求职信、导出 PDF、记录申请进度和批量处理太分散的问题，"
        "做法是把这些步骤串成 Claude Code、Codex、Gemini 等 Agent Skill CLI 里的求职流水线。"
        "它省掉的是反复复制 JD、人工筛岗位、手改简历和求职信、维护申请表、逐个导出 PDF 这些重复步骤；"
        "README 给出的使用信号是已经评估 740+ 个职位、生成 100+ 份个性化 CV，并帮助拿到 1 个目标岗位。"
    )
}
README_SUMMARY_OVERRIDES_PATH = PROJECT_ROOT / "config" / "readme_summary_overrides_zh.json"
_README_SUMMARY_OVERRIDES_CACHE: dict[str, str] | None = None


def readme_summary_overrides() -> dict[str, str]:
    global _README_SUMMARY_OVERRIDES_CACHE
    if _README_SUMMARY_OVERRIDES_CACHE is not None:
        return _README_SUMMARY_OVERRIDES_CACHE

    overrides: dict[str, str] = {
        str(name): str(summary).strip()
        for name, summary in README_SUMMARY_OVERRIDES.items()
        if str(summary).strip()
    }
    if README_SUMMARY_OVERRIDES_PATH.exists():
        try:
            loaded = json.loads(README_SUMMARY_OVERRIDES_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[warn] 读取 README 摘要覆盖表失败: {exc}", file=sys.stderr)
        else:
            if isinstance(loaded, dict):
                for name, summary in loaded.items():
                    clean = str(summary or "").strip()
                    if clean:
                        overrides[str(name)] = clean
            else:
                print(f"[warn] README 摘要覆盖表不是 JSON object: {README_SUMMARY_OVERRIDES_PATH}", file=sys.stderr)
    _README_SUMMARY_OVERRIDES_CACHE = overrides
    return overrides

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

    def get_raw_text(self, url: str) -> str | None:
        headers = {
            "Accept-Encoding": "identity",
            "Connection": "close",
            "User-Agent": USER_AGENT,
        }
        cmd = [
            "curl",
            "--http1.1",
            "-L",
            "-sS",
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
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if completed.returncode != 0:
                return None
            body, status_text = completed.stdout.rsplit("\n", 1)
            return body if int(status_text) < 400 else None
        except (ValueError, OSError):
            return None

    def get_readme_text(self, full_name: str, default_branch: str = "main") -> str | None:
        encoded_name = urllib.parse.quote(full_name, safe="/")
        try:
            data = self.request_json(f"/repos/{encoded_name}/readme")
        except GithubApiError:
            data = None

        if isinstance(data, dict):
            content = data.get("content")
            encoding = data.get("encoding")
        else:
            content = None
            encoding = None
        if content and encoding == "base64":
            try:
                raw = base64.b64decode(content).decode("utf-8", errors="replace")
                return raw
            except (ValueError, UnicodeError):
                pass

        branch = urllib.parse.quote(default_branch or "main", safe="")
        for filename in ["README.md", "readme.md", "README.MD", "README"]:
            path = urllib.parse.quote(filename, safe="/")
            raw = self.get_raw_text(f"https://raw.githubusercontent.com/{full_name}/{branch}/{path}")
            if raw:
                return raw
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


def has_chinese_text(value: str | None) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", value or ""))


def has_long_english_text(value: str | None) -> bool:
    return bool(re.search(r"[A-Za-z]{4,}", value or ""))


def looks_like_readme_noise(line: str) -> bool:
    clean = line.strip()
    if not clean:
        return True

    lower = clean.lower()
    if re.fullmatch(r"[\s|:.\-–—_·•]+", clean):
        return True
    if re.search(r"shields\.io|badge|stargazers|network/members|graphs/contributors", lower):
        return True
    if lower.startswith(("license", "sponsor", "stars ", "forks ", "discord ", "website ")):
        return True
    if clean.count("|") >= 3 and any(word in lower for word in README_LANGUAGE_WORDS):
        return True
    if any(word in lower for word in README_LANGUAGE_WORDS) and re.search(r"\s[|·]\s|&nbsp;| / ", lower):
        return True
    if re.fullmatch(r"(?:\[[^\]]*\]\([^)]*\)\s*){2,}", clean):
        return True
    if len(re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "", clean)) < 3:
        return True
    return False


def readme_plain_lines(text: str | None) -> list[str]:
    if not text:
        return []

    lines: list[str] = []
    in_code_block = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block or looks_like_readme_noise(line):
            continue
        if line.startswith(("#", "-", "*", ">")):
            line = line.lstrip("#-* >").strip()
        if looks_like_readme_noise(line):
            continue
        line = clean_markdown(line)
        if not looks_like_readme_noise(line):
            lines.append(line)
    return lines


def first_readme_excerpt(text: str | None, max_chars: int) -> str:
    lines: list[str] = []
    for line in readme_plain_lines(text):
        lines.append(line)
        if sum(len(item) for item in lines) >= max_chars:
            break
    excerpt = " ".join(lines)
    return excerpt[:max_chars].strip()


def compact_sentence(value: str, max_chars: int = 180) -> str:
    value = clean_markdown(value)
    value = re.sub(r"\s+", " ", value).strip(" .;:|")
    if len(value) <= max_chars:
        return value
    shortened = value[:max_chars].rsplit(" ", 1)[0].strip(" .;:|")
    return shortened or value[:max_chars].strip(" .;:|")


def readable_repo_title(repo: dict[str, Any]) -> str:
    name = str(repo.get("name") or repo.get("full_name") or "这个项目").strip()
    return name.replace("-", " ").replace("_", " ").strip() or "这个项目"


def doc_text_for_summary(repo: dict[str, Any]) -> str:
    examples = []
    for example in repo.get("examples") or []:
        if not isinstance(example, dict):
            continue
        examples.extend([example.get("title"), example.get("body"), example.get("code")])
    return " ".join(
        str(item)
        for item in [
            repo.get("full_name"),
            repo.get("name"),
            repo.get("description"),
            repo.get("readme_excerpt"),
            *(repo.get("topics") or []),
            *examples,
        ]
        if item
    ).lower()


def summary_kind_from_docs(repo: dict[str, Any], text: str) -> tuple[str, str, str, str]:
    if re.search(
        r"\b(job search|career|resume|cv|cover letter|interview prep|job applications?|application tracker|application tracking)\b",
        text,
    ):
        return (
            "AI 求职管理系统",
            "正在找工作、需要批量筛选岗位和定制投递材料的候选人",
            "手动判断岗位匹配度、改简历/CV、写求职信、导出 PDF、记录申请进度太分散",
            "把岗位评估、材料生成、PDF 输出、申请记录和批量处理串成一套求职流水线。",
        )
    if re.search(
        r"\b(token consumption|token optimization|cost reduction|token savings|compresses?|compression|reduce[sd]? llm token|token killer)\b",
        text,
    ):
        return (
            "AI 编程成本优化工具",
            "频繁使用 Claude Code、Codex、Cursor 等 AI 编程工具的开发者",
            "命令输出太长、上下文被无效内容塞满，导致 token 和费用浪费",
            "压缩命令输出、减少无效上下文或统计模型消耗，让同样的开发任务少花 token 和费用。",
        )
    if re.search(r"\b(design|wireframe|mockup|ui generator|html artifacts|slides|deck|poster)\b", text):
        return (
            "设计/原型生成工具",
            "需要快速看见方案效果的产品、设计和内容创作者",
            "想法停留在文字里，很难判断页面、海报、幻灯片或原型是否可用",
            "把文字需求快速转成界面、海报、幻灯片、网页原型或可预览的视觉物料。",
        )
    if re.search(r"\b(html editor|html page|web page|landing page|surface|hyperframe)\b", text):
        return (
            "HTML 页面生成工具",
            "要快速产出网页、报告或社交媒体物料的创作者和产品同学",
            "普通文档不够直观，自己写 HTML 又慢",
            "把文字草稿或需求变成可预览、可发布的网页、报告、海报或社交媒体内容。",
        )
    if re.search(r"\b(deepseek|terminal|cli|coding agent|code agent|agentic coding)\b", text):
        return (
            "终端里的 AI 编程助手",
            "习惯在终端或编辑器里工作的工程师",
            "希望 AI 直接参与读代码、改代码、跑命令，但又不想离开现有开发流程",
            "把模型能力接进命令行工作流，让 AI 在项目里执行代码修改、测试和排错任务。",
        )
    if re.search(r"\b(agent harness|skills?, instincts?|agent shield|rules?)\b", text):
        return (
            "AI 编程技能/规则包",
            "已经在用 Claude Code、Codex、Cursor 等 AI 编程工具的开发者或团队",
            "AI 做任务时容易忘上下文、流程不稳定、代码风格和安全边界不一致",
            "把提示词、流程、记忆、安全检查或开发习惯整理成可复用规则，让 AI 更稳定地完成开发任务。",
        )
    if re.search(r"\b(awesome|curated list|resources|roadmap|collection of)\b", text):
        return (
            "资料合集",
            "想快速补课、选型或找同类项目参考的人",
            "相关工具和教程分散，自己从头搜索会花很多时间",
            "把同类工具、教程、模板或资源集中整理出来，方便快速建立地图和候选池。",
        )
    if re.search(r"\b(api client|postman|rest|graphql|http client|api testing)\b", text):
        return (
            "接口调试工具",
            "后端、前端和测试同学",
            "接口请求、返回结果和测试用例不好管理，协作时容易散落在不同工具里",
            "集中管理 API 请求、测试响应和接口用例，替代或补充 Postman 这类工作流。",
        )
    if re.search(r"\b(browser automation|puppeteer|playwright|web automation|browser harness)\b", text):
        return (
            "浏览器自动化工具",
            "需要做网页测试、自动化操作或网页数据采集的开发者",
            "人工点网页、复现流程和检查页面状态耗时且容易漏步骤",
            "自动打开网页、点击、抓取内容或跑端到端测试，把重复浏览器操作流程化。",
        )
    if re.search(r"\b(game engine|2d game|lua|live reload|cross-platform export)\b", text):
        return (
            "2D 游戏开发工具",
            "想快速做小游戏或交互原型的开发者",
            "从零搭游戏循环、预览和跨平台导出成本高",
            "提供 2D 游戏原型、实时预览和导出能力，让想法更快变成可玩的 demo。",
        )
    if re.search(r"\b(cryptographic|untrusted server|encrypted|collaborative applications)\b", text):
        return (
            "加密协作框架",
            "要做安全协作应用的技术团队或研究者",
            "多人协作时服务端不一定可信，但数据仍需要保持隐私和一致性",
            "用加密协议和协作框架来保护协作数据，研究不可信服务器下的应用架构。",
        )
    if re.search(r"\b(copilot studio|microsoft 365|declarative agents|m365)\b", text):
        return (
            "Microsoft 365 Copilot 智能体模板",
            "想在 Microsoft 365 里快速落地 Copilot Agent 的企业用户",
            "业务部门想试智能体，但从零写配置和接办公流程门槛高",
            "提供可复制的声明式智能体配置，让办公场景能更快试用 Copilot Agent。",
        )
    if re.search(r"\b(markdown vault|obsidian|logseq|wiki|second brain|knowledge wiki)\b", text):
        return (
            "个人知识库增强工具",
            "长期用 Markdown、Obsidian 或 Logseq 记录资料的人",
            "笔记越积越多后，AI 很难持续理解关联和复用历史上下文",
            "把本地笔记整理成可增长的知识系统，让 AI 能读、关联和复用长期资料。",
        )
    if re.search(r"\b(workflow|automation|visual canvas|rag|human-in-the-loop|n8n alternative)\b", text):
        return (
            "AI 工作流自动化工具",
            "想把 AI 接进业务流程的运营、产品或工程团队",
            "单次对话不能沉淀成稳定流程，人工确认、知识库和外部工具也难串起来",
            "把提示词、知识库、人工确认、外部工具和自动化步骤编排成可反复运行的工作流。",
        )
    if re.search(r"\b(data app|dashboard|streamlit|visualization|analytics|chart)\b", text):
        return (
            "数据应用搭建工具",
            "有脚本、表格或模型结果要展示给别人看的数据/业务团队",
            "结果只停留在代码或表格里，非技术同学难以操作和理解",
            "把数据、脚本或模型结果做成可交互页面，让别人不用看代码也能查看和操作。",
        )
    if re.search(r"\b(mcp|tool calling|connect apps|real actions|send emails|slack|github issues)\b", text):
        return (
            "AI 工具连接项目",
            "想让 AI 真正操作外部系统的开发者和自动化团队",
            "AI 只回答问题但不能安全地发邮件、查表、建 issue 或调用业务工具",
            "把邮件、表格、GitHub、Slack 等外部应用接进 AI 流程，让模型能执行真实动作。",
        )
    if re.search(r"\b(framework|sdk|library|package|server|runtime)\b", text):
        return (
            "开发者框架/工具包",
            "需要接入底层能力或搭建上层产品的工程团队",
            "从零封装基础能力成本高，重复造轮子会拖慢产品验证",
            "提供框架、SDK、库或运行时，让开发者更快接入能力并构建自己的产品。",
        )
    return (
        "开发者工具项目",
        "需要评估新工具是否值得试用的开发者或产品同学",
        "只看 stars 和标题很难判断真实用途、上手门槛和是否适合自己的场景",
        "结合 README、项目说明、示例截图和最近提交来判断它解决的问题和使用方式。",
    )


def doc_detail_hints(text: str) -> list[str]:
    hints: list[str] = []
    checks = [
        (r"\b(pdf|ats-optimized|ats optimized)\b", "PDF 输出"),
        (r"\b(batch|bulk)\b", "批量处理"),
        (r"\b(scan|scanner)\b", "自动扫描"),
        (r"\b(dashboard|kanban|tracker)\b", "看板/记录追踪"),
        (r"\b(agent skill standard|skill-standard)\b", "Agent Skill 标准 CLI"),
        (r"\b(local-first|local first)\b", "本地优先"),
        (r"\b(sandbox|preview)\b", "沙盒预览"),
        (r"\b(one[- ]click|1-click)\b", "一键操作"),
        (r"\b(open source|open-source)\b", "开源"),
        (r"\b(multi[- ]agent|parallel agents?)\b", "多智能体协作"),
    ]
    for pattern, label in checks:
        if re.search(pattern, text) and label not in hints:
            hints.append(label)
    return hints


def compact_metric_signal(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" .;:|")
    return value[:90].strip(" .;:|")


def metric_signal_to_zh(signal: str, text: str) -> str:
    signal = compact_metric_signal(signal)
    lower_signal = signal.lower()
    lower_text = text.lower()

    skills_surfaces = re.search(r"(\d+\+?)\s*skills?\s*[×x]\s*(\d+\+?)\s*surfaces?", lower_signal)
    if skills_surfaces:
        return f"{skills_surfaces.group(1)} 个技能、{skills_surfaces.group(2)} 个输出场景。"

    skills = re.search(r"(\d+\+?)\s*skills?", lower_signal)
    design_systems = re.search(r"(\d+\+?)\s*design systems?", lower_signal)
    if skills and design_systems:
        return f"{skills.group(1)} 个技能、{design_systems.group(1)} 套设计系统。"

    under_time = re.search(r"under\s+(\d+(?:\.\d+)?)\s*(minutes|mins|hours|hrs|seconds|weeks)", lower_signal)
    if under_time:
        unit = {
            "seconds": "秒",
            "minutes": "分钟",
            "mins": "分钟",
            "hours": "小时",
            "hrs": "小时",
            "weeks": "周",
        }[under_time.group(2)]
        return f"{under_time.group(1)} {unit}内可以完成上手。"

    percent = re.search(r"(-?\d{1,3}(?:\s*-\s*\d{1,3})?)\s*%", signal)
    if percent:
        value = percent.group(1).replace(" ", "").lstrip("-") + "%"
        if any(keyword in lower_text for keyword in ["token", "llm", "command output", "dev command"]):
            return f"常见开发命令可减少 {value} 的模型 token 消耗。"
        if any(keyword in lower_text for keyword in ["saving", "cost", "compress"]):
            return f"README 提到有 {value} 的节省幅度。"
        return f"README 提到有 {value} 的效率或节省幅度。"

    time_value = re.search(
        r"(<\s*)?(\d+(?:\.\d+)?)\s*(ms|milliseconds|seconds|minutes|mins|hours|hrs|weeks)",
        lower_signal,
    )
    if time_value:
        prefix = "小于 " if time_value.group(1) else ""
        unit = {
            "ms": "毫秒",
            "milliseconds": "毫秒",
            "seconds": "秒",
            "minutes": "分钟",
            "mins": "分钟",
            "hours": "小时",
            "hrs": "小时",
            "weeks": "周",
        }[time_value.group(3)]
        if "overhead" in lower_signal or "overhead" in lower_text:
            return f"额外耗时约 {prefix}{time_value.group(2)} {unit}。"
        return f"耗时约 {prefix}{time_value.group(2)} {unit}。"

    count = re.search(
        r"(\d+\+?)\s*(personalized cvs|supported commands|design systems|flagship models|coding-agent clis|job listings|contributors|repositories|templates|surfaces|skills|models|agents|apps|clis)",
        lower_signal,
    )
    if count:
        labels = {
            "job listings": "个职位",
            "personalized cvs": "份个性化 CV",
            "supported commands": "个支持命令",
            "apps": "个应用",
            "skills": "个技能",
            "surfaces": "个输出场景",
            "contributors": "位贡献者",
            "models": "个模型",
            "repositories": "个仓库",
            "templates": "个模板",
            "agents": "个智能体",
            "design systems": "套设计系统",
            "coding-agent clis": "个 AI 编程 CLI",
            "clis": "个 CLI",
            "flagship models": "个旗舰模型",
        }
        return f"{count.group(1)} {labels[count.group(2)]}。"

    return signal


def quantitative_evidence_text(text: str) -> str:
    patterns = [
        r"\b\d+\+?\s*skills?\s*[×x]\s*\d+\+?\s*surfaces?\b",
        r"\b\d+\+?\s*skills?\b[^.;|]{0,50}\b\d+\+?\s*design systems?\b",
        r"\b\d{1,3}\s*-\s*\d{1,3}%(?!\w)",
        r"(?<!\w)-?\d{1,3}%(?!\w)",
        r"\b\d+\+?\s*(?:personalized cvs|supported commands|design systems|flagship models|coding-agent clis|job listings|contributors|repositories|templates|surfaces|skills|models|agents|apps|clis)\b",
        r"\bunder\s+\d+(?:\.\d+)?\s*(?:minutes|mins|hours|hrs|seconds|weeks)\b",
        r"<\s*\d+(?:\.\d+)?\s*(?:ms|milliseconds|seconds|minutes|mins|hours|hrs)\b",
        r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds|seconds|minutes|mins|hours|hrs|weeks)\b",
    ]
    signals: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            signal = metric_signal_to_zh(match.group(0), text)
            if "%" in signal and any("%" in existing for existing in signals):
                continue
            if "分钟" in signal and any("分钟" in existing for existing in signals):
                continue
            if any(marker in signal and any(marker in existing for existing in signals) for marker in ["个技能", "套设计系统"]):
                continue
            if signal and signal not in signals:
                signals.append(signal)
            if len(signals) >= 2:
                break
        if len(signals) >= 2:
            break
    if not signals:
        return ""
    return f"README 里能看到的量化信号包括：{'；'.join(signal.rstrip('。') for signal in signals)}。"


def savings_text_from_docs(kind: str, text: str) -> str:
    if kind == "AI 求职管理系统":
        return "它省掉的是反复复制 JD、人工筛岗位、手改简历和求职信、维护申请表、逐个导出 PDF 这些重复步骤。"
    if kind == "AI 编程成本优化工具":
        return "它省掉的是人工清理冗长命令输出、反复压缩上下文和事后追查 token 消耗的步骤，收益主要体现在少花模型额度和少花钱。"
    if kind == "终端里的 AI 编程助手":
        return "它省掉的是在聊天窗口、编辑器和终端之间来回切换、手动复制报错、再手动执行测试的步骤，把读代码、改代码、跑命令集中到一个流程里。"
    if kind == "AI 编程技能/规则包":
        return "它省掉的是每次都重新写提示词、重复解释项目规则、人工补安全约束和手动纠偏 AI 输出的步骤。"
    if kind == "资料合集":
        return "它省掉的是逐个搜索、收藏、筛选和对比资料的时间，把补课和选型的前置搜索集中到一处。"
    if kind == "接口调试工具":
        return "它省掉的是手动整理接口地址、复制请求参数、保存返回结果和重复搭测试用例的步骤。"
    if kind == "浏览器自动化工具":
        return "它省掉的是人工点网页、重复复现路径、手动截图和逐项检查页面状态的步骤。"
    if kind == "2D 游戏开发工具":
        return "它省掉的是从零搭游戏循环、热更新、预览和导出链路的基础工程时间。"
    if kind == "加密协作框架":
        return "它省掉的是团队从零设计加密同步协议、权限边界和不可信服务端协作模型的研究成本。"
    if kind == "Microsoft 365 Copilot 智能体模板":
        return "它省掉的是从零写 Copilot Agent 配置、整理业务提示词和接入办公流程的启动步骤。"
    if kind == "个人知识库增强工具":
        return "它省掉的是人工翻旧笔记、手动建立关联、反复给 AI 补背景资料的步骤。"
    if kind == "AI 工作流自动化工具":
        return "它省掉的是把同一套 AI 任务反复人工发起、手动复制结果、再切换外部工具执行下一步的流程成本。"
    if kind == "设计/原型生成工具":
        return "它省掉的是先写需求、再找设计工具、再手工做页面/海报/幻灯片初稿的步骤，让想法更快变成可看的稿子。"
    if kind == "HTML 页面生成工具":
        return "它省掉的是手写 HTML、调样式、跑预览和重复导出页面素材的步骤。"
    if kind == "数据应用搭建工具":
        return "它省掉的是把脚本结果截图发给别人、手动做表格说明、再反复解释数据含义的沟通步骤。"
    if kind == "AI 工具连接项目":
        return "它省掉的是在 AI 回答后再人工打开邮箱、表格、GitHub 或 Slack 执行操作的步骤，把回答和动作接在一起。"
    if kind == "开发者框架/工具包":
        return "它省掉的是从零封装底层能力、写样板代码和重复搭集成链路的工程时间。"
    return "它省掉的是先点开仓库再人工判断用途、上手路径和投入成本的筛选时间。"


def summarize_repo_docs_zh(repo: dict[str, Any]) -> str:
    full_name = str(repo.get("full_name") or "")
    overrides = readme_summary_overrides()
    if full_name in overrides:
        return overrides[full_name]

    description = compact_sentence(str(repo.get("description") or ""), 220)
    excerpt = compact_sentence(str(repo.get("readme_excerpt") or ""), 360)
    source = description or excerpt
    if source and has_chinese_text(source) and not has_long_english_text(source):
        return source

    text = doc_text_for_summary(repo)
    kind, audience, problem, solution = summary_kind_from_docs(repo, text)
    title = readable_repo_title(repo)
    hints = doc_detail_hints(text)
    examples = [
        str(example.get("title") or "").strip()
        for example in repo.get("examples") or []
        if isinstance(example, dict) and str(example.get("title") or "").strip()
    ]

    article = "一个 " if re.match(r"^[A-Za-z0-9]", kind) else "一个"
    pieces = [f"{title} 是{article}{kind}，主要给{audience}用。它解决的是{problem}，做法是{solution}"]
    pieces.append(savings_text_from_docs(kind, text))
    evidence = quantitative_evidence_text(text)
    if evidence:
        pieces.append(evidence)
    if hints:
        pieces.append(f"README 和仓库信息里能看到的关键能力包括：{'、'.join(hints[:4])}。")
    if examples:
        pieces.append(f"README 还给了 {'、'.join(examples[:2])} 这类上手/使用部分，可以直接看示例判断是否值得试。")
    return "".join(pieces)


def attach_repo_doc_summary(repo: dict[str, Any]) -> None:
    repo["readme_summary_zh"] = summarize_repo_docs_zh(repo)


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


def meets_min_stars(repo: dict[str, Any], config: dict[str, Any]) -> bool:
    min_stars = int(config.get("min_stars") or 0)
    if min_stars <= 0:
        return True
    return int(repo.get("stars") or 0) >= min_stars


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
    open_issues = int(repo.get("open_issues") or 0)
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
    readme_bonus = 35 if repo.get("readme_excerpt") else 0
    example_bonus = 55 if repo.get("examples") else 0
    homepage_bonus = 18 if repo.get("homepage") else 0
    license_bonus = 8 if repo.get("license") else 0
    docs_bonus = readme_bonus + example_bonus + homepage_bonus + license_bonus
    hot_score = rising_score + min(frontier_signal * 0.35, 65)
    used_score = (
        min(math.sqrt(max(forks, 0)) * 8, 420)
        + min(math.log10(max(stars, 1)) * 70, 360)
        + min(math.sqrt(max(open_issues, 0)) * 3.5, 130)
        + freshness * 1.4
        + docs_bonus
        + min(feature_bonus * 1.3, 95)
        + expert_signal_weight * 0.25
    )
    starred_score = all_time_score
    discussion_score = (
        min(math.sqrt(max(open_issues, 0)) * 14, 440)
        + min(math.sqrt(max(forks, 0)) * 7, 300)
        + min(math.log10(max(stars, 1)) * 55, 290)
        + min(delta_per_day * 20, 220)
        + freshness * 1.2
        + min(feature_bonus, 70)
        + expert_signal_weight * 0.2
    )

    repo["age_days"] = age_days
    repo["star_velocity"] = round(star_velocity, 2)
    repo["delta_stars"] = delta_stars
    repo["delta_days"] = delta_days
    repo["delta_per_day"] = round(delta_per_day, 2)
    repo["expert_score"] = round(expert_raw_score, 3)
    repo["scores"] = {
        "hot": round(hot_score, 2),
        "used": round(used_score, 2),
        "starred": round(starred_score, 2),
        "discussion": round(discussion_score, 2),
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
    if list_name == "热度榜":
        reason = f"最近增长和更新信号更强，适合优先判断是不是新趋势。{delta}"
    elif list_name == "大家都在用榜":
        reason = (
            f"已有 {compact_int(repo.get('forks'))} 个分支，README / 示例 / 更新状态会一起参与评分，"
            "更偏向能直接试用或改造的项目。"
        )
    elif list_name == "高收藏榜":
        reason = f"累计 {compact_int(repo.get('stars'))} 个收藏，说明它已经被大量开发者长期认可。"
    elif list_name == "参与讨论榜":
        reason = (
            f"当前有 {compact_int(repo.get('open_issues'))} 个公开 issue，"
            f"{compact_int(repo.get('forks'))} 个分支，适合观察社区反馈和协作热度。"
        )
    else:
        reason = "适合作为选题池里的候选项目继续观察。"
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
今天刷到一个 GitHub 项目 {repo['full_name']}，适合关注 AI 工具、职业效率、办公学习、内容创作和自动化应用的人收藏。

项目是做什么的：
{intro}

核心功能：
{feature_lines}

为什么现在值得看：
目前 {compact_int(repo['stars'])} 个星标，创建于 {repo.get('created_at', '')[:10]}，最近仍有更新{delta_text}。如果你在找近一年值得关注的应用、小工具、职业提效方案或 AI 自动化产品，可以重点看它的产品思路、上手路径和 README 里的真实场景。

可展开讲的角度：
- 它解决了哪类人群或职业场景里的具体痛点
- 它和传统软件、手工流程或普通 AI 对话有什么不同
- 哪个功能最适合做成小红书截图或录屏演示

项目链接：
{repo['html_url']}

标签：
#GitHub #开源项目 #AI工具 #效率工具 #自动化 #职业提效"""
    return body


def build_markdown(
    run_date: dt.date,
    hot: list[dict[str, Any]],
    used: list[dict[str, Any]],
    starred: list[dict[str, Any]],
    discussion: list[dict[str, Any]],
    xhs_repos: list[dict[str, Any]],
    config: dict[str, Any],
) -> str:
    generated_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    lines = [
        f"# GitHub 近一年好项目趋势榜 - {run_date.isoformat()}",
        "",
        f"生成时间：{generated_at}",
        "",
        "## 今日摘要",
        "",
        f"- 热度榜收录 {len(hot)} 个项目，主要看近一年项目的最近涨星、更新、项目年龄和热点方向。",
        f"- 大家都在用榜收录 {len(used)} 个项目，主要看 fork、文档示例、维护状态和可直接试用程度。",
        f"- 高收藏榜收录 {len(starred)} 个项目，主要看累计星标、分支和长期认可度。",
        f"- 参与讨论榜收录 {len(discussion)} 个项目，主要看 issue、fork、最近更新和社区协作痕迹。",
        "- 第一次运行时没有历史涨星数据；连续运行后，“最近涨星”会越来越准。",
        "",
        "## 热度榜",
        "",
    ]

    if hot:
        for index, repo in enumerate(hot, 1):
            lines.append(repo_card(repo, index, "热度榜"))
            lines.append("")
    else:
        lines.extend(["没有拿到符合默认热度查询的项目。", ""])

    lines.extend(["## 大家都在用榜", ""])
    if used:
        for index, repo in enumerate(used, 1):
            lines.append(repo_card(repo, index, "大家都在用榜"))
            lines.append("")
    else:
        lines.extend(["没有拿到有明显使用痕迹的项目。", ""])

    lines.extend(
        [
        "## 高收藏榜",
        "",
        ]
    )

    if starred:
        for index, repo in enumerate(starred, 1):
            lines.append(repo_card(repo, index, "高收藏榜"))
            lines.append("")
    else:
        lines.extend(["没有拿到高收藏项目。", ""])

    lines.extend(["## 参与讨论榜", ""])
    if discussion:
        for index, repo in enumerate(discussion, 1):
            lines.append(repo_card(repo, index, "参与讨论榜"))
            lines.append("")
    else:
        lines.extend(["没有拿到有明显公开讨论的项目。", ""])

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
            f"- 时间口径：主榜以近 {config.get('trend_window_days', 365)} 天创建或近一年仍活跃的项目为主，不再聚焦 90 天早期项目。",
            f"- 星标口径：候选项目最低 {config.get('min_stars', 100)} stars，上限不封顶；高 stars 项目会进入成熟参考或高收藏视角。",
            "- 人物/专家观察源：只读取公开 GitHub star、配置里的公开推文链接和项目引用，不采集私信、私有收藏或登录后内容。",
            "- 搜索范围：覆盖 AI 工具、浏览器插件、桌面应用、知识管理、写作、内容生产、自动化、低代码，以及产品、运营、设计、销售、研究、教育、财务等职业效率工具。",
            "- 热度榜：看最近涨星、星标速度、最近更新、近一年成长和热点关键词。",
            "- 大家都在用榜：看 fork、README、截图示例、官网、维护状态和可直接试用程度。",
            "- 高收藏榜：看 stars、forks、维护状态和长期认可度。",
            "- 参与讨论榜：看 open issues、forks、最近更新和社区协作痕迹。",
            "- 同一个项目只放进一个榜单；冲突时按热度榜、大家都在用榜、参与讨论榜、高收藏榜的顺序归类。",
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
    hot: list[dict[str, Any]],
    used: list[dict[str, Any]],
    starred: list[dict[str, Any]],
    discussion: list[dict[str, Any]],
    xhs_repos: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[Path, Path]:
    day_dir = paths.output_dir / run_date.isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)

    markdown = build_markdown(run_date, hot, used, starred, discussion, xhs_repos, config)
    markdown_path = day_dir / "github-web-coding-daily.md"
    json_path = day_dir / "repos.json"
    markdown_path.write_text(markdown, encoding="utf-8")
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "date": run_date.isoformat(),
                "hot": hot,
                "used": used,
                "starred": starred,
                "discussion": discussion,
                "frontier": hot,
                "product_ideas": used,
                "all_time": starred,
                "rising": hot,
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


def iter_payload_repos(payload: dict[str, Any]) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for section in PAYLOAD_REPO_SECTIONS:
        for repo in payload.get(section) or []:
            full_name = repo.get("full_name")
            if not full_name or full_name in seen:
                continue
            seen.add(full_name)
            repos.append(repo)
    return repos


def attach_payload_doc_summaries(payload: dict[str, Any]) -> int:
    updated = 0
    seen: set[int] = set()
    for section in PAYLOAD_REPO_SECTIONS:
        for repo in payload.get(section) or []:
            if not isinstance(repo, dict):
                continue
            marker = id(repo)
            if marker in seen:
                continue
            seen.add(marker)
            summary = summarize_repo_docs_zh(repo)
            if repo.get("readme_summary_zh") != summary:
                repo["readme_summary_zh"] = summary
                updated += 1
    return updated


def collect_readme_assets_from_payload(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    for repo in iter_payload_repos(payload):
        full_name = repo.get("full_name")
        if not full_name:
            continue
        current = assets.setdefault(full_name, {})
        if repo.get("readme_excerpt") and not current.get("readme_excerpt"):
            current["readme_excerpt"] = repo["readme_excerpt"]
        examples = repo.get("examples")
        if isinstance(examples, list) and examples and not current.get("examples"):
            current["examples"] = examples
    return assets


def iter_payload_images(payload: dict[str, Any]) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    seen_repos: set[str] = set()
    for section in PAYLOAD_IMAGE_SECTIONS:
        for repo in payload.get(section) or []:
            full_name = repo.get("full_name")
            if not full_name:
                continue
            if section == "all_repos" and full_name in seen_repos:
                continue
            seen_repos.add(full_name)
            for example in repo.get("examples") or []:
                if not isinstance(example, dict):
                    continue
                for image in example.get("images") or []:
                    if isinstance(image, dict) and image.get("url"):
                        images.append(image)
    return images


def is_local_readme_image_url(url: str) -> bool:
    clean_url = url.lstrip("/")
    return clean_url.startswith(f"{LOCAL_README_IMAGE_BASE}/")


def normalize_readme_image_url(url: str) -> str:
    clean_url = url.strip()
    lower_url = clean_url.lower()
    for suffix in GITHUB_README_IMAGE_MODE_SUFFIXES:
        if lower_url.endswith(suffix):
            return clean_url[: -len(suffix)]
    return clean_url


def image_extension_from_url(url: str) -> str:
    normalized_url = normalize_readme_image_url(url)
    suffix = Path(urllib.parse.urlparse(normalized_url).path).suffix.lower()
    return suffix if suffix in IMAGE_FILE_EXTENSIONS else ""


def image_content_type_from_headers(path: Path) -> str:
    try:
        headers = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    content_types = re.findall(r"(?im)^content-type:\s*([^;\r\n]+)", headers)
    if not content_types:
        return ""
    return content_types[-1].strip().lower()


def image_extension_from_headers(path: Path) -> str:
    content_type = image_content_type_from_headers(path)
    return IMAGE_CONTENT_TYPE_EXTENSIONS.get(content_type, "")


def cached_readme_image_path(url: str, asset_dir: Path = LOCAL_README_IMAGE_DIR) -> Path | None:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    matches = sorted(asset_dir.glob(f"{digest}.*"))
    return matches[0] if matches else None


def optimize_readme_image(path: Path, extension: str) -> Path:
    if extension not in OPTIMIZABLE_README_IMAGE_EXTENSIONS:
        return path
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return path

    optimized_path = path.with_suffix(".webp")
    try:
        with Image.open(path) as image:
            if getattr(image, "is_animated", False):
                return path
            image = ImageOps.exif_transpose(image)
            if image.width > OPTIMIZED_README_IMAGE_MAX_WIDTH:
                height = max(1, round(image.height * OPTIMIZED_README_IMAGE_MAX_WIDTH / image.width))
                image = image.resize((OPTIMIZED_README_IMAGE_MAX_WIDTH, height), Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            image.save(optimized_path, "WEBP", quality=OPTIMIZED_README_IMAGE_QUALITY, method=6)
    except Exception as exc:
        print(f"Image optimize skipped: {path.name} ({exc})", file=sys.stderr)
        try:
            if optimized_path.exists():
                optimized_path.unlink()
        except OSError:
            pass
        return path

    try:
        if optimized_path.stat().st_size < path.stat().st_size:
            path.unlink()
            return optimized_path
        optimized_path.unlink()
    except OSError:
        return path
    return path


def env_nonnegative_number(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        number = float(value)
    except ValueError:
        return default
    if number < 0:
        return default
    return str(int(number) if number.is_integer() else number)


def download_readme_image(url: str, asset_dir: Path = LOCAL_README_IMAGE_DIR) -> str | None:
    url = normalize_readme_image_url(url)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None

    cached = cached_readme_image_path(url, asset_dir)
    if cached:
        return f"{LOCAL_README_IMAGE_BASE}/{cached.name}"

    asset_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    temp_path = asset_dir / f"{digest}.download"
    headers_path = asset_dir / f"{digest}.headers"
    retry_count = env_nonnegative_number("README_IMAGE_CURL_RETRY", "2")
    connect_timeout = env_nonnegative_number("README_IMAGE_CONNECT_TIMEOUT", "15")
    max_time = env_nonnegative_number("README_IMAGE_CURL_MAX_TIME", "45")
    cmd = [
        "curl",
        "-L",
        "-sS",
        "--retry",
        retry_count,
        "--retry-all-errors",
        "--connect-timeout",
        connect_timeout,
        "--max-time",
        max_time,
        "-A",
        USER_AGENT,
        "-D",
        str(headers_path),
        "-o",
        str(temp_path),
        url,
    ]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not temp_path.exists() or temp_path.stat().st_size == 0:
            print(f"Image cache skipped: {url} ({completed.stderr.strip() or completed.returncode})", file=sys.stderr)
            return None
        content_type = image_content_type_from_headers(headers_path)
        header_extension = IMAGE_CONTENT_TYPE_EXTENSIONS.get(content_type, "")
        if content_type and not header_extension and content_type not in IMAGE_EXTENSION_FALLBACK_CONTENT_TYPES:
            print(f"Image cache skipped: {url} (non-image content type: {content_type})", file=sys.stderr)
            return None
        extension = header_extension or image_extension_from_url(url)
        if not extension:
            print(f"Image cache skipped: {url} (unknown image type)", file=sys.stderr)
            return None
        final_path = asset_dir / f"{digest}{extension}"
        temp_path.replace(final_path)
        final_path = optimize_readme_image(final_path, extension)
        return f"{LOCAL_README_IMAGE_BASE}/{final_path.name}"
    finally:
        for path in [temp_path, headers_path]:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass


def localize_payload_images(payload: dict[str, Any], asset_dir: Path = LOCAL_README_IMAGE_DIR) -> int:
    localized = 0
    for section in PAYLOAD_IMAGE_SECTIONS:
        for repo in payload.get(section) or []:
            for example in repo.get("examples") or []:
                if not isinstance(example, dict):
                    continue
                kept_images = []
                for image in example.get("images") or []:
                    if not isinstance(image, dict):
                        continue
                    url = str(image.get("url") or "").strip()
                    if not url:
                        continue
                    if is_local_readme_image_url(url):
                        kept_images.append(image)
                        continue
                    local_url = download_readme_image(url, asset_dir)
                    if not local_url:
                        continue
                    image.setdefault("source_url", url)
                    image["url"] = local_url
                    kept_images.append(image)
                    localized += 1
                example["images"] = kept_images
    return localized


def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def bootstrap_history_from_payload(history: dict[str, Any], payload: dict[str, Any]) -> int:
    date_text = str(payload.get("date") or "").strip()
    if not date_text:
        return 0
    try:
        dt.date.fromisoformat(date_text)
    except ValueError:
        return 0

    repos_history = history.setdefault("repos", {})
    added = 0
    for repo in iter_payload_repos(payload):
        full_name = repo.get("full_name")
        if not full_name:
            continue
        snapshots = repos_history.setdefault(full_name, [])
        if any(snapshot.get("date") == date_text for snapshot in snapshots):
            continue
        snapshots.append(
            {
                "date": date_text,
                "stars": safe_int(repo.get("stars")),
                "forks": safe_int(repo.get("forks")),
                "open_issues": safe_int(repo.get("open_issues")),
            }
        )
        added += 1
    return added


def extract_embedded_radar_payload_from_text(html_text: str) -> dict[str, Any] | None:
    match = EMBEDDED_RADAR_DATA_RE.search(html_text)
    if not match:
        return None
    try:
        payload = json.loads(match.group(2))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def load_embedded_radar_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return extract_embedded_radar_payload_from_text(path.read_text(encoding="utf-8"))
    except OSError:
        return None


def json_for_embedded_script(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def embed_radar_payload(html_text: str, payload: dict[str, Any]) -> str:
    embedded = json_for_embedded_script(payload)
    updated, count = EMBEDDED_RADAR_DATA_RE.subn(
        lambda match: f"{match.group(1)}{embedded}{match.group(3)}",
        html_text,
        count=1,
    )
    if count != 1:
        raise ValueError("embedded radar data script tag not found")
    return updated


def embed_latest_json(args: argparse.Namespace) -> int:
    data_path = Path(args.data).resolve()
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{data_path} must contain a JSON object")
    summary_count = attach_payload_doc_summaries(payload)
    if summary_count:
        print(f"Refreshed Chinese README summaries: {summary_count}")
    if not getattr(args, "skip_localize_images", False):
        localized = localize_payload_images(payload)
        if localized:
            print(f"Localized README images: {localized}")

    files = [Path(file).resolve() for file in args.files]
    for html_path in files:
        html_text = html_path.read_text(encoding="utf-8")
        html_path.write_text(embed_radar_payload(html_text, payload), encoding="utf-8")
        print(f"Embedded radar data: {html_path}")
    return 0


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
                if not meets_min_stars(repo, config):
                    continue
                if repo["full_name"] in merged:
                    merge_repo(merged[repo["full_name"]], repo)
                else:
                    merged[repo["full_name"]] = repo

    for repo in collect_expert_repositories(client, config):
        if not repo.get("full_name"):
            continue
        if not meets_min_stars(repo, config):
            continue
        if repo["full_name"] in merged:
            merge_repo(merged[repo["full_name"]], repo)
        else:
            merged[repo["full_name"]] = repo

    return list(merged.values())


def load_previous_readme_assets(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    assets: dict[str, dict[str, Any]] = {}
    for section in ["all_repos", "frontier", "product_ideas", "all_time", "rising", "xhs_repos"]:
        for repo in payload.get(section) or []:
            full_name = repo.get("full_name")
            if not full_name:
                continue
            current = assets.setdefault(full_name, {})
            if repo.get("readme_excerpt") and not current.get("readme_excerpt"):
                current["readme_excerpt"] = repo["readme_excerpt"]
            examples = repo.get("examples")
            if isinstance(examples, list) and examples and not current.get("examples"):
                current["examples"] = examples
    return assets


def restore_previous_readme_assets(
    repos: list[dict[str, Any]],
    previous_assets: dict[str, dict[str, Any]],
    history: dict[str, Any],
    run_date: dt.date,
) -> int:
    restored = 0
    for repo in repos:
        previous = previous_assets.get(repo["full_name"])
        if not previous:
            continue

        changed = False
        if not repo.get("readme_excerpt") and previous.get("readme_excerpt"):
            repo["readme_excerpt"] = previous["readme_excerpt"]
            changed = True
        if not repo.get("examples") and previous.get("examples"):
            repo["examples"] = previous["examples"]
            changed = True
        if changed:
            repo["features"] = infer_features(repo)
            attach_repo_doc_summary(repo)
            score_repo(repo, history, run_date)
            restored += 1
    return restored


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
    if max_readmes <= 0:
        readme_targets = {repo["full_name"] for repo in likely_interesting}
    else:
        readme_targets = {repo["full_name"] for repo in likely_interesting[:max_readmes]}

    for repo in repos:
        if repo["full_name"] in readme_targets:
            readme_text = client.get_readme_text(repo["full_name"], repo.get("default_branch") or "main")
            repo["readme_excerpt"] = first_readme_excerpt(readme_text, readme_chars)
            repo["examples"] = extract_readme_examples(
                readme_text,
                full_name=repo["full_name"],
                default_branch=repo.get("default_branch") or "main",
            )
        repo["features"] = infer_features(repo)
        attach_repo_doc_summary(repo)
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
    hot_limit = int(config.get("hot_limit", config.get("rising_limit", 15)))
    used_limit = int(config.get("used_limit", config.get("product_limit", 15)))
    starred_limit = int(config.get("starred_limit", config.get("top_limit", 20)))
    discussion_limit = int(config.get("discussion_limit", config.get("frontier_limit", 15)))
    xhs_count = int(config.get("xhs_count", 5))
    rising_max_age_days = int(config.get("rising_max_age_days", 180))

    # 同一个项目只进一个榜单，避免不同标签页里重复出现。
    # 认领顺序：先保留最近变热和真实使用痕迹，再给讨论活跃项目留位置，最后补高收藏经典项目。
    claimed: set[str] = set()

    def take(candidates: list[dict[str, Any]], score_key: str, limit: int) -> list[dict[str, Any]]:
        ranked = sorted(
            (repo for repo in candidates if repo["full_name"] not in claimed),
            key=lambda repo: float((repo.get("scores") or {}).get(score_key, 0)),
            reverse=True,
        )[:limit]
        for repo in ranked:
            claimed.add(repo["full_name"])
        return ranked

    hot_candidates = [
        repo
        for repo in repos
        if "rising" in repo.get("sources", [])
        or repo.get("age_days", 9999) <= rising_max_age_days
        or float(repo.get("delta_per_day") or 0) > 0
        or float(repo.get("star_velocity") or 0) >= 5
        or repo.get("lens", {}).get("frontier_hits")
    ]
    if not hot_candidates:
        hot_candidates = repos
    hot = take(hot_candidates, "hot", hot_limit)

    used_candidates = [
        repo
        for repo in repos
        if "product" in repo.get("sources", [])
        or "all_time" in repo.get("sources", [])
        or int(repo.get("forks") or 0) >= 20
        or repo.get("examples")
        or repo.get("readme_excerpt")
        or repo.get("homepage")
        or "Web IDE / Browser Editor" in repo.get("features", [])
        or "Low-code / No-code" in repo.get("features", [])
        or "Sandbox / Preview" in repo.get("features", [])
    ]
    if not used_candidates:
        used_candidates = repos
    used = take(used_candidates, "used", used_limit)

    discussion_candidates = [
        repo
        for repo in repos
        if int(repo.get("open_issues") or 0) > 0
        or int(repo.get("forks") or 0) >= 10
        or repo.get("expert_signals")
    ]
    if not discussion_candidates:
        discussion_candidates = repos
    discussion = take(discussion_candidates, "discussion", discussion_limit)

    starred_candidates = [repo for repo in repos if "all_time" in repo.get("sources", []) or int(repo.get("stars") or 0) > 0]
    if not starred_candidates:
        starred_candidates = repos
    starred = take(starred_candidates, "starred", starred_limit)

    seen: set[str] = set()
    xhs_repos: list[dict[str, Any]] = []
    for repo in used + hot + discussion + starred:
        if repo["full_name"] in seen:
            continue
        seen.add(repo["full_name"])
        xhs_repos.append(repo)
        if len(xhs_repos) >= xhs_count:
            break
    return hot, used, starred, discussion, xhs_repos


def run(args: argparse.Namespace) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    config = load_config(Path(args.config).resolve())
    if args.hot_limit is not None:
        config["hot_limit"] = args.hot_limit
    if args.used_limit is not None:
        config["used_limit"] = args.used_limit
    if args.starred_limit is not None:
        config["starred_limit"] = args.starred_limit
    if args.discussion_limit is not None:
        config["discussion_limit"] = args.discussion_limit
    if args.top_limit is not None:
        config["top_limit"] = args.top_limit
        config.setdefault("starred_limit", args.top_limit)
    if args.frontier_limit is not None:
        config["frontier_limit"] = args.frontier_limit
        config.setdefault("discussion_limit", args.frontier_limit)
    if args.product_limit is not None:
        config["product_limit"] = args.product_limit
        config.setdefault("used_limit", args.product_limit)
    if args.rising_limit is not None:
        config["rising_limit"] = args.rising_limit
        config.setdefault("hot_limit", args.rising_limit)
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
    embedded_payload = load_embedded_radar_payload(PROJECT_ROOT / "radar.html")
    if embedded_payload and not history.get("repos"):
        bootstrapped = bootstrap_history_from_payload(history, embedded_payload)
        if bootstrapped:
            print(f"Bootstrapped history from embedded radar data: {bootstrapped} repos")

    repos = collect_repositories(client, config, run_date)
    enrich_repositories(client, repos, config, history, run_date)
    previous_readme_assets = load_previous_readme_assets(paths.output_dir / "latest.json")
    if not previous_readme_assets and embedded_payload:
        previous_readme_assets = collect_readme_assets_from_payload(embedded_payload)
    restored_readme_assets = restore_previous_readme_assets(
        repos,
        previous_readme_assets,
        history,
        run_date,
    )
    hot, used, starred, discussion, xhs_repos = select_rankings(repos, config)
    update_history(paths.data_path, history, repos, run_date)
    markdown_path, json_path = write_outputs(
        paths, run_date, repos, hot, used, starred, discussion, xhs_repos, config
    )

    print(f"Generated: {markdown_path}")
    print(f"JSON: {json_path}")
    print(f"Repos collected: {len(repos)}")
    print(f"Hot ranking: {len(hot)}")
    print(f"Used ranking: {len(used)}")
    print(f"Starred ranking: {len(starred)}")
    print(f"Discussion ranking: {len(discussion)}")
    print(f"XHS drafts: {len(xhs_repos)}")
    if restored_readme_assets:
        print(f"Restored README assets from previous run: {restored_readme_assets}")
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
        description="每天帮你找好项目：生成近一年 GitHub 应用、效率工具、AI 自动化和成熟参考榜单。"
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="collect repos and generate the daily report")
    run_parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    run_parser.add_argument("--date", help="run date, YYYY-MM-DD")
    run_parser.add_argument("--hot-limit", type=int)
    run_parser.add_argument("--used-limit", type=int)
    run_parser.add_argument("--starred-limit", type=int)
    run_parser.add_argument("--discussion-limit", type=int)
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

    embed_parser = subparsers.add_parser("embed", help="embed generated latest JSON into static radar pages")
    embed_parser.add_argument("--data", default=str(PROJECT_ROOT / "output" / "latest.json"))
    embed_parser.add_argument(
        "--skip-localize-images",
        action="store_true",
        help="skip downloading README images while embedding the latest JSON",
    )
    embed_parser.add_argument(
        "files",
        nargs="*",
        default=[str(PROJECT_ROOT / "radar.html"), str(PROJECT_ROOT / "public" / "radar.html")],
    )
    embed_parser.set_defaults(func=embed_latest_json)

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
