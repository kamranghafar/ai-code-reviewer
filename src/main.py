"""AI Code Reviewer - GitHub Action Entry Point."""

import json
import os
import sys

from reviewer import CodeReviewer
from github_client import GitHubClient
from ai_client import AIClient


def get_input(name: str, default: str = "") -> str:
    """Get GitHub Action input."""
    val = os.environ.get(f"INPUT_{name.upper().replace('-', '_')}", "")
    return val if val else default


def set_output(name: str, value: str) -> None:
    """Set GitHub Action output."""
    output_file = os.environ.get("GITHUB_OUTPUT", "")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")


def main() -> int:
    """Run the AI code reviewer."""
    # Parse inputs
    openai_api_key = get_input("openai_api_key")
    github_token = get_input("github_token", os.environ.get("GITHUB_TOKEN", ""))
    model = get_input("model", "gpt-4o-mini")
    review_level = get_input("review_level", "standard")
    language_filter = get_input("language", "")
    severity_threshold = get_input("severity_threshold", "info")
    max_files = int(get_input("max_files", "0"))
    exclude_patterns = get_input("exclude_patterns", "")
    post_summary = get_input("post_summary", "true").lower() == "true"

    if not openai_api_key:
        print("::error::OpenAI API key is required. Set the 'openai_api_key' input.")
        return 1

    if not github_token:
        print("::error::GitHub token is required.")
        return 1

    # Parse event
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path or not os.path.exists(event_path):
        print("::error::Could not find GitHub event payload.")
        return 1

    with open(event_path) as f:
        event = json.load(f)

    pr_number = event.get("pull_request", {}).get("number")
    if not pr_number:
        print("::error::This action only works on pull_request events.")
        return 1

    repo_full_name = event.get("repository", {}).get("full_name", "")
    if not repo_full_name:
        repo_full_name = os.environ.get("GITHUB_REPOSITORY", "")

    print(f"🔍 Reviewing PR #{pr_number} in {repo_full_name}")
    print(f"   Model: {model} | Level: {review_level} | Severity: {severity_threshold}")

    # Initialize clients
    gh_client = GitHubClient(github_token, repo_full_name)
    ai_client = AIClient(openai_api_key, model)
    reviewer = CodeReviewer(
        gh_client=gh_client,
        ai_client=ai_client,
        review_level=review_level,
        language_filter=language_filter,
        severity_threshold=severity_threshold,
        max_files=max_files,
        exclude_patterns=exclude_patterns,
    )

    # Fetch PR diff
    print("📥 Fetching PR diff...")
    files = gh_client.get_pr_files(pr_number)

    if not files:
        print("✅ No reviewable files found in this PR.")
        return 0

    print(f"📂 Found {len(files)} file(s) to review")

    # Run review
    print("🤖 Running AI review...")
    results = reviewer.review_files(files, pr_number)

    # Post inline comments
    print("💬 Posting review comments...")
    comments_posted = gh_client.post_review_comments(pr_number, results.comments)
    print(f"   Posted {comments_posted} inline comment(s)")

    # Post summary
    if post_summary:
        print("📊 Posting review summary...")
        gh_client.post_summary_comment(pr_number, results.summary)

    # Set outputs
    set_output("review_score", str(results.score))
    set_output("issues_found", str(results.total_issues))
    set_output("critical_issues", str(results.critical_issues))

    print(f"\n{'='*50}")
    print(f"📋 Review Complete!")
    print(f"   Score: {results.score}/100")
    print(f"   Issues: {results.total_issues} total, {results.critical_issues} critical")
    print(f"{'='*50}")

    # Fail if critical issues found
    if results.critical_issues > 0:
        print(f"::warning::Found {results.critical_issues} critical issue(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
