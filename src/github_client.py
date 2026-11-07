"""GitHub API client for PR interactions."""

import re
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class PRFile:
    """Represents a file changed in a PR."""
    filename: str
    status: str
    patch: str
    additions: int
    deletions: int
    language: str


class GitHubClient:
    """Client for GitHub API interactions."""

    API_BASE = "https://api.github.com"

    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
        ".cpp": "C++",
        ".c": "C",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".scala": "Scala",
        ".sh": "Shell",
        ".bash": "Shell",
        ".yml": "YAML",
        ".yaml": "YAML",
        ".json": "JSON",
        ".xml": "XML",
        ".html": "HTML",
        ".css": "CSS",
        ".sql": "SQL",
        ".tf": "Terraform",
        ".dockerfile": "Dockerfile",
    }

    REVIEWABLE_EXTENSIONS = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
        ".rb", ".php", ".cs", ".cpp", ".c", ".swift", ".kt", ".scala",
        ".sh", ".bash", ".tf", ".sql",
    }

    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _detect_language(self, filename: str) -> str:
        """Detect programming language from file extension."""
        lower = filename.lower()
        if lower.endswith("dockerfile") or lower.startswith("dockerfile"):
            return "Dockerfile"
        for ext, lang in self.LANGUAGE_MAP.items():
            if lower.endswith(ext):
                return lang
        return "Unknown"

    def _is_reviewable(self, filename: str) -> bool:
        """Check if a file should be reviewed."""
        lower = filename.lower()
        if lower.endswith("dockerfile") or lower.startswith("dockerfile"):
            return True
        return any(lower.endswith(ext) for ext in self.REVIEWABLE_EXTENSIONS)

    def get_pr_files(self, pr_number: int) -> list[PRFile]:
        """Fetch changed files for a PR."""
        url = f"{self.API_BASE}/repos/{self.repo}/pulls/{pr_number}/files"
        files = []
        page = 1

        while True:
            resp = self.session.get(url, params={"per_page": 100, "page": page})
            resp.raise_for_status()
            data = resp.json()

            if not data:
                break

            for f in data:
                if f.get("status") == "removed":
                    continue
                if not self._is_reviewable(f["filename"]):
                    continue
                patch = f.get("patch", "")
                if not patch:
                    continue

                files.append(PRFile(
                    filename=f["filename"],
                    status=f["status"],
                    patch=patch,
                    additions=f.get("additions", 0),
                    deletions=f.get("deletions", 0),
                    language=self._detect_language(f["filename"]),
                ))

            if len(data) < 100:
                break
            page += 1

        return files

    def get_pr_details(self, pr_number: int) -> dict:
        """Get PR metadata."""
        url = f"{self.API_BASE}/repos/{self.repo}/pulls/{pr_number}"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()

    def post_review_comments(
        self, pr_number: int, comments: list[dict]
    ) -> int:
        """Post inline review comments on a PR."""
        if not comments:
            return 0

        url = f"{self.API_BASE}/repos/{self.repo}/pulls/{pr_number}/reviews"

        # Build review with inline comments
        review_comments = []
        for c in comments:
            comment = {
                "path": c["path"],
                "body": c["body"],
            }
            if c.get("line"):
                comment["line"] = c["line"]
                comment["side"] = "RIGHT"
            elif c.get("position"):
                comment["position"] = c["position"]

            review_comments.append(comment)

        if not review_comments:
            return 0

        payload = {
            "body": "🤖 **AI Code Review** — automated review by [ai-code-reviewer](https://github.com/kamranghafar/ai-code-reviewer)",
            "event": "COMMENT",
            "comments": review_comments,
        }

        try:
            resp = self.session.post(url, json=payload)
            resp.raise_for_status()
            return len(review_comments)
        except requests.HTTPError as e:
            print(f"::warning::Failed to post some review comments: {e}")
            # Try posting comments individually as fallback
            posted = 0
            for rc in review_comments:
                try:
                    single_payload = {
                        "body": rc["body"],
                        "event": "COMMENT",
                        "comments": [rc],
                    }
                    resp = self.session.post(url, json=single_payload)
                    resp.raise_for_status()
                    posted += 1
                except requests.HTTPError:
                    continue
            return posted

    def post_summary_comment(self, pr_number: int, summary: str) -> None:
        """Post a summary comment on the PR."""
        url = f"{self.API_BASE}/repos/{self.repo}/issues/{pr_number}/comments"
        payload = {"body": summary}
        try:
            resp = self.session.post(url, json=payload)
            resp.raise_for_status()
        except requests.HTTPError as e:
            print(f"::warning::Failed to post summary comment: {e}")
