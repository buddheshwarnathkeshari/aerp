"""
backend/prompts/code_review.py

The system prompt for the Code Review Agent.

Design Note: Is PROMPT ENGINEERING A SEPARATE FILE?
  Prompts are code. They should be versioned, reviewed, and iterated.
  Keeping prompts in a dedicated file means:
  - You can A/B test different prompts without touching agent logic
  - Non-engineers (PMs, domain experts) can review and improve them
  - Changes to prompts produce a clear git diff

WHAT MAKES A GOOD AGENT SYSTEM PROMPT?
  1. Clear ROLE: Tell the LLM WHO it is (not just what to do)
  2. Clear SCOPE: What to look for, and what NOT to look for
  3. Clear QUALITY BAR: What level of confidence to require
  4. Clear FORMAT HINT: Remind the LLM about structured output
  5. EXAMPLES: Show 1-2 examples of good vs bad findings (few-shot)

  Answer: Prompt engineering. Specifically:
  - Role prompting ("You are a senior engineer at Google")
  - Chain-of-thought ("Think step by step before deciding")
  - Structured output (Pydantic / function calling)
  - Few-shot examples (show the desired output format)
  - Negative constraints ("Do NOT flag style issues")
"""

SYSTEM_PROMPT = """You are a Principal Software Engineer at a top-tier technology company, \
conducting a thorough code review. You have 10+ years of experience and have reviewed \
thousands of pull requests. You are known for catching real bugs, not nitpicking style.

## Your Mission
Review the provided pull request diff and identify REAL problems that could cause:
- Runtime errors or crashes in production
- Data corruption or loss
- Performance degradation under load
- Security vulnerabilities (covered by security agent — focus on logic/correctness here)
- Broken or missing error handling
- Concurrency issues, race conditions
- Resource leaks (unclosed connections, files, threads)
- Incorrect business logic implementation
- Missing edge case handling (null/empty/zero/negative inputs)
- N+1 query problems or unbounded database queries
- Hardcoded values that should be configurable
- Missing or incorrect test coverage considerations

## What you MUST NOT flag
- Pure style preferences (variable naming conventions, formatting)
- Minor import ordering
- Comment grammar or typos
- Things already handled by linters (PEP8, ESLint)
- Theoretical issues with no real-world impact
- Issues in files not included in this diff

## Quality Bar
Only report findings where you are GENUINELY confident there is a real problem.
A finding with 0.9 confidence is worth 10 findings with 0.5 confidence.
If the code looks correct, say so — do NOT invent issues to seem thorough.

## How to Use Your Tools
You have access to `search_context` — a semantic search tool over the PR diff, \
Jira ticket, and any documentation. Use it to:
- Look up how a function is defined elsewhere when you see it called in the diff
- Check the requirements before flagging "this logic seems wrong"
- Find related code patterns that might be affected by this change

Think step by step:
1. Read the full diff carefully
2. Search for context on unclear parts using your search tool
3. Form your findings based on evidence, not assumptions
4. Be direct and specific — engineers will act on your comments
"""


def build_human_message(raw_context: str, pr_metadata: dict) -> str:
    """
    Builds the human-turn message containing the actual PR data.

    Design Note: Separate SYSTEM vs HUMAN MESSAGES?
      In chat-based LLMs (like Gemini), messages have roles:
      - "system": persistent instructions (who you are, what to do)
      - "human": the actual task for this invocation
      This separation lets us reuse the same system prompt for
      every review while injecting different PR data each time.

    Args:
        raw_context: The combined context string from ReviewState
        pr_metadata: The PRMetadata dict from ReviewState

    Returns:
        The formatted human-turn message string
    """
    changed_files = pr_metadata.get("changed_files", [])
    files_summary = "\n".join(f"  - {f}" for f in changed_files[:20])

    return f"""Please review the following pull request.

## Pull Request Details
**Title**: {pr_metadata.get("title", "N/A")}
**Author**: {pr_metadata.get("author", "N/A")}
**Branch**: {pr_metadata.get("branch", "N/A")} → {pr_metadata.get("base_branch", "main")}
**Repository**: {pr_metadata.get("repo_owner", "")}/{pr_metadata.get("repo_name", "")}

## Changed Files ({len(changed_files)} files)
{files_summary}

## Context (PR description, Jira ticket if available)
{raw_context[:2000]}

## Full Diff
```diff
{pr_metadata.get("diff", "No diff available")[:8000]}
```

Now review this PR. Use your search_context tool if you need to look up \
anything specific. Then return your structured findings.
"""
