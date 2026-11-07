"""OpenAI API client for code review."""

import json
from typing import Optional

from openai import OpenAI


SYSTEM_PROMPT = """You are an expert code reviewer with deep expertise in software engineering, 
security, and best practices. You review code changes (diffs) and provide actionable, specific feedback.

Your review must cover these categories:
1. **Security Vulnerabilities** — injection, auth issues, secrets exposure, unsafe deserialization, SSRF, path traversal
2. **Code Smells** — dead code, overly complex functions, magic numbers, poor naming, code duplication
3. **Best Practices** — error handling, input validation, logging, documentation, type safety
4. **Performance** — N+1 queries, unnecessary allocations, blocking calls, algorithmic complexity
5. **Reliability** — race conditions, resource leaks, missing null checks, unhandled edge cases

For each issue found, respond with a JSON object in this exact format:
{
  "issues": [
    {
      "line": <line_number_in_diff_or_null>,
      "severity": "error|warning|info",
      "category": "security|code-smell|best-practice|performance|reliability",
      "title": "Short descriptive title",
      "description": "Detailed explanation of the issue",
      "suggestion": "Concrete code fix or improvement (use markdown code blocks if applicable)"
    }
  ],
  "score": <0-100>,
  "summary": "Brief overall assessment (2-3 sentences)"
}

Scoring guide:
- 90-100: Excellent, minor suggestions only
- 70-89: Good, some improvements recommended
- 50-69: Fair, notable issues that should be addressed
- 30-49: Poor, significant issues found
- 0-29: Critical, blocking issues that must be fixed

Rules:
- Be specific — reference actual code from the diff
- Be constructive — always suggest fixes, not just problems
- Ignore style/formatting unless it impacts readability significantly
- Focus on the CHANGED lines (lines starting with +), not removed lines
- Prioritize security and reliability over style
- Return valid JSON only, no extra text"""


REVIEW_LEVEL_PROMPTS = {
    "quick": "Do a quick review focusing only on critical security issues and obvious bugs. Be concise.",
    "standard": "Do a standard review covering security, bugs, best practices, and performance. Be thorough but practical.",
    "thorough": "Do an exhaustive review. Check every aspect: security, performance, reliability, maintainability, testability, documentation. Be very detailed.",
}


class AIClient:
    """Client for OpenAI API interactions."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def review_diff(
        self,
        filename: str,
        language: str,
        diff: str,
        review_level: str = "standard",
        context: Optional[str] = None,
    ) -> dict:
        """Send a diff to OpenAI for review."""
        level_prompt = REVIEW_LEVEL_PROMPTS.get(review_level, REVIEW_LEVEL_PROMPTS["standard"])

        user_prompt = f"""{level_prompt}

**File:** `{filename}`
**Language:** {language}

**Diff to review:**
```diff
{diff}
```"""

        if context:
            user_prompt += f"\n\n**Additional context:** {context}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=4096,
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except json.JSONDecodeError:
            print(f"::warning::Failed to parse AI response for {filename}")
            return {"issues": [], "score": 50, "summary": "Review could not be parsed."}
        except Exception as e:
            print(f"::warning::AI review failed for {filename}: {e}")
            return {"issues": [], "score": 50, "summary": f"Review error: {str(e)}"}
