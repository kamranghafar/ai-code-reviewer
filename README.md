# 🤖 AI Code Reviewer

[![GitHub Action](https://img.shields.io/badge/GitHub-Action-blue?logo=github)](https://github.com/kamranghafar/ai-code-reviewer)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenAI](https://img.shields.io/badge/Powered%20by-OpenAI-412991?logo=openai)](https://openai.com)

**AI-powered code reviewer that automatically reviews your Pull Requests** — catches security vulnerabilities, code smells, performance issues, and suggests actionable fixes using OpenAI.

---

## ✨ Features

- 🔒 **Security Scanning** — Detects injection flaws, secrets exposure, auth issues, SSRF, path traversal
- 👃 **Code Smell Detection** — Dead code, complexity, magic numbers, poor naming, duplication
- 📏 **Best Practice Enforcement** — Error handling, input validation, type safety, documentation
- ⚡ **Performance Analysis** — N+1 queries, unnecessary allocations, algorithmic complexity
- 🛡️ **Reliability Checks** — Race conditions, resource leaks, null safety, edge cases
- 📊 **Review Summary** — Score (0-100) with grade, per-file breakdown, and category stats
- 🌍 **Multi-Language** — Python, JavaScript, TypeScript, Java, Go, Rust, and more

## 🚀 Quick Start

Add this workflow to your repository at `.github/workflows/ai-review.yml`:

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: AI Code Review
        uses: kamranghafar/ai-code-reviewer@v1
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
          model: 'gpt-4o-mini'
          review_level: 'standard'
```

> **Setup:** Add your OpenAI API key as a repository secret named `OPENAI_API_KEY`.

## ⚙️ Configuration

| Input | Description | Default | Required |
|-------|-------------|---------|----------|
| `openai_api_key` | OpenAI API key | — | ✅ |
| `github_token` | GitHub token for PR access | `${{ github.token }}` | No |
| `model` | OpenAI model (`gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`) | `gpt-4o-mini` | No |
| `review_level` | Review depth: `quick`, `standard`, `thorough` | `standard` | No |
| `language` | Comma-separated language filter (auto-detect if empty) | `""` | No |
| `severity_threshold` | Minimum severity: `info`, `warning`, `error` | `info` | No |
| `max_files` | Max files to review (0 = unlimited) | `0` | No |
| `exclude_patterns` | Glob patterns to exclude (e.g. `"*.md,tests/*"`) | `""` | No |
| `post_summary` | Post summary comment with score | `true` | No |

### Outputs

| Output | Description |
|--------|-------------|
| `review_score` | Overall code quality score (0-100) |
| `issues_found` | Total number of issues found |
| `critical_issues` | Number of critical/error-level issues |

### Review Levels

| Level | Description | Best For |
|-------|-------------|----------|
| `quick` | Security issues and obvious bugs only | Large PRs, fast feedback |
| `standard` | Security + bugs + best practices + performance | Daily development |
| `thorough` | Exhaustive review of every aspect | Critical code, releases |

## 📋 Example Review Output

### Inline Comments

> 🔴 **ERROR** | 🔒 security
>
> ### SQL Injection Vulnerability
>
> The query string is constructed using f-string interpolation with user input, which is vulnerable to SQL injection attacks.
>
> **💡 Suggestion:**
> ```python
> # Instead of:
> cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
>
> # Use parameterized queries:
> cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
> ```

### Summary Comment

> ## 🤖 AI Code Review Summary
>
> | Metric | Value |
> |--------|-------|
> | **Score** | 62/100 (C) |
> | **Verdict** | ⚠️ Needs Improvement |
> | **Files Reviewed** | 4 |
> | **Total Issues** | 7 |
> | **Critical Issues** | 2 |

## 🌍 Supported Languages

| Language | Extensions |
|----------|------------|
| Python | `.py` |
| JavaScript | `.js`, `.jsx` |
| TypeScript | `.ts`, `.tsx` |
| Java | `.java` |
| Go | `.go` |
| Rust | `.rs` |
| Ruby | `.rb` |
| PHP | `.php` |
| C# | `.cs` |
| C/C++ | `.c`, `.cpp` |
| Swift | `.swift` |
| Kotlin | `.kt` |
| Scala | `.scala` |
| Shell | `.sh`, `.bash` |
| Terraform | `.tf` |
| SQL | `.sql` |

## 📂 Advanced Examples

### Only review security-critical issues

```yaml
- uses: kamranghafar/ai-code-reviewer@v1
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    review_level: 'quick'
    severity_threshold: 'error'
```

### Review only Python and JavaScript files

```yaml
- uses: kamranghafar/ai-code-reviewer@v1
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    language: 'python,javascript'
```

### Thorough review excluding tests

```yaml
- uses: kamranghafar/ai-code-reviewer@v1
  with:
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    model: 'gpt-4o'
    review_level: 'thorough'
    exclude_patterns: 'tests/*,*_test.py,*.spec.ts'
```

### Use review score in subsequent steps

```yaml
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: AI Code Review
        id: review
        uses: kamranghafar/ai-code-reviewer@v1
        with:
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}

      - name: Check quality gate
        if: steps.review.outputs.critical_issues > 0
        run: |
          echo "::error::Code review found ${{ steps.review.outputs.critical_issues }} critical issues"
          echo "Review score: ${{ steps.review.outputs.review_score }}/100"
```

## 🔒 Security

- Your OpenAI API key is passed as a secret and never logged
- Code diffs are sent to OpenAI's API for analysis — review your OpenAI data policies
- The action uses the `GITHUB_TOKEN` with minimal required permissions
- No code is stored or cached outside of the review process

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Kamran Ghaffar** — Senior QA/DevOps Engineer

- GitHub: [@kamranghafar](https://github.com/kamranghafar)

---

<p align="center">
  <sub>Built with ❤️ for better code reviews</sub>
</p>
