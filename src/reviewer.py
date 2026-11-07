"""Code review orchestrator."""

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Optional

from github_client import GitHubClient, PRFile
from ai_client import AIClient


SEVERITY_LEVELS = {"info": 0, "warning": 1, "error": 2}

SEVERITY_EMOJI = {
    "error": "🔴",
    "warning": "🟡",
    "info": "🔵",
}

CATEGORY_EMOJI = {
    "security": "🔒",
    "code-smell": "👃",
    "best-practice": "📏",
    "performance": "⚡",
    "reliability": "🛡️",
}


@dataclass
class ReviewResults:
    """Aggregated review results."""
    comments: list[dict] = field(default_factory=list)
    score: int = 100
    total_issues: int = 0
    critical_issues: int = 0
    summary: str = ""
    file_scores: dict = field(default_factory=dict)


class CodeReviewer:
    """Orchestrates the code review process."""

    def __init__(
        self,
        gh_client: GitHubClient,
        ai_client: AIClient,
        review_level: str = "standard",
        language_filter: str = "",
        severity_threshold: str = "info",
        max_files: int = 0,
        exclude_patterns: str = "",
    ):
        self.gh = gh_client
        self.ai = ai_client
        self.review_level = review_level
        self.language_filter = (
            [lang.strip().lower() for lang in language_filter.split(",") if lang.strip()]
            if language_filter
            else []
        )
        self.severity_threshold = SEVERITY_LEVELS.get(severity_threshold, 0)
        self.max_files = max_files
        self.exclude_patterns = (
            [p.strip() for p in exclude_patterns.split(",") if p.strip()]
            if exclude_patterns
            else []
        )

    def _should_review(self, file: PRFile) -> bool:
        """Check if a file should be reviewed based on filters."""
        # Language filter
        if self.language_filter:
            if file.language.lower() not in self.language_filter:
                return False

        # Exclude patterns
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file.filename, pattern):
                return False

        return True

    def _parse_diff_line_numbers(self, patch: str) -> dict[int, int]:
        """Map diff positions to actual file line numbers."""
        line_map = {}
        position = 0
        current_line = 0

        for line in patch.split("\n"):
            if line.startswith("@@"):
                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                match = re.search(r"\+(\d+)", line)
                if match:
                    current_line = int(match.group(1)) - 1
                position += 1
                continue

            position += 1

            if line.startswith("-"):
                # Deleted line — no new line number
                continue
            elif line.startswith("+"):
                current_line += 1
                line_map[position] = current_line
            else:
                current_line += 1
                line_map[position] = current_line

        return line_map

    def _format_comment_body(self, issue: dict) -> str:
        """Format a single issue as a review comment."""
        severity = issue.get("severity", "info")
        category = issue.get("category", "general")
        title = issue.get("title", "Issue found")
        description = issue.get("description", "")
        suggestion = issue.get("suggestion", "")

        sev_emoji = SEVERITY_EMOJI.get(severity, "ℹ️")
        cat_emoji = CATEGORY_EMOJI.get(category, "📝")

        body = f"{sev_emoji} **{severity.upper()}** | {cat_emoji} {category}\n\n"
        body += f"### {title}\n\n"
        body += f"{description}\n\n"

        if suggestion:
            body += f"**💡 Suggestion:**\n{suggestion}\n"

        return body

    def _build_summary(self, results: ReviewResults, files: list[PRFile]) -> str:
        """Build the summary comment."""
        score = results.score
        total = results.total_issues
        critical = results.critical_issues

        # Score badge
        if score >= 90:
            grade = "A"
            color = "brightgreen"
            verdict = "✅ Excellent"
        elif score >= 70:
            grade = "B"
            color = "green"
            verdict = "👍 Good"
        elif score >= 50:
            grade = "C"
            color = "yellow"
            verdict = "⚠️ Needs Improvement"
        elif score >= 30:
            grade = "D"
            color = "orange"
            verdict = "🔶 Poor"
        else:
            grade = "F"
            color = "red"
            verdict = "🔴 Critical Issues"

        summary = f"""## 🤖 AI Code Review Summary

| Metric | Value |
|--------|-------|
| **Score** | {score}/100 ({grade}) |
| **Verdict** | {verdict} |
| **Files Reviewed** | {len(results.file_scores)} |
| **Total Issues** | {total} |
| **Critical Issues** | {critical} |

"""
        # Category breakdown
        categories = {}
        for comment in results.comments:
            cat = comment.get("category", "general")
            sev = comment.get("severity", "info")
            if cat not in categories:
                categories[cat] = {"error": 0, "warning": 0, "info": 0}
            categories[cat][sev] = categories[cat].get(sev, 0) + 1

        if categories:
            summary += "### 📊 Issues by Category\n\n"
            summary += "| Category | 🔴 Error | 🟡 Warning | 🔵 Info |\n"
            summary += "|----------|----------|------------|----------|\n"
            for cat, counts in sorted(categories.items()):
                emoji = CATEGORY_EMOJI.get(cat, "📝")
                summary += f"| {emoji} {cat} | {counts.get('error', 0)} | {counts.get('warning', 0)} | {counts.get('info', 0)} |\n"
            summary += "\n"

        # Per-file scores
        if results.file_scores:
            summary += "### 📁 File Scores\n\n"
            summary += "| File | Score | Issues |\n"
            summary += "|------|-------|--------|\n"
            for fname, info in sorted(results.file_scores.items()):
                s = info["score"]
                icon = "🟢" if s >= 80 else ("🟡" if s >= 50 else "🔴")
                summary += f"| `{fname}` | {icon} {s}/100 | {info['issues']} |\n"
            summary += "\n"

        summary += "---\n"
        summary += "*Automated review by [ai-code-reviewer](https://github.com/kamranghafar/ai-code-reviewer) — "
        summary += f"powered by OpenAI*\n"

        return summary

    def review_files(self, files: list[PRFile], pr_number: int) -> ReviewResults:
        """Review all files and aggregate results."""
        results = ReviewResults()
        reviewable = [f for f in files if self._should_review(f)]

        if self.max_files > 0:
            reviewable = reviewable[: self.max_files]

        if not reviewable:
            results.summary = "No files matched the review criteria."
            return results

        all_scores = []

        for file in reviewable:
            print(f"   Reviewing {file.filename} ({file.language})...")

            review = self.ai.review_diff(
                filename=file.filename,
                language=file.language,
                diff=file.patch,
                review_level=self.review_level,
            )

            file_score = review.get("score", 50)
            all_scores.append(file_score)
            issues = review.get("issues", [])

            # Map diff lines
            line_map = self._parse_diff_line_numbers(file.patch)
            file_issue_count = 0

            for issue in issues:
                severity = issue.get("severity", "info")
                sev_level = SEVERITY_LEVELS.get(severity, 0)

                if sev_level < self.severity_threshold:
                    continue

                file_issue_count += 1
                results.total_issues += 1

                if severity == "error":
                    results.critical_issues += 1

                # Build comment
                comment = {
                    "path": file.filename,
                    "body": self._format_comment_body(issue),
                    "severity": severity,
                    "category": issue.get("category", "general"),
                }

                # Try to map to a line number
                issue_line = issue.get("line")
                if issue_line:
                    # Find closest diff position for this line
                    best_position = None
                    for pos, actual_line in line_map.items():
                        if actual_line == issue_line:
                            best_position = pos
                            break
                    if best_position:
                        comment["position"] = best_position
                    else:
                        comment["line"] = issue_line

                results.comments.append(comment)

            results.file_scores[file.filename] = {
                "score": file_score,
                "issues": file_issue_count,
            }

        # Compute aggregate score
        if all_scores:
            results.score = round(sum(all_scores) / len(all_scores))

        # Build summary
        results.summary = self._build_summary(results, reviewable)

        return results
