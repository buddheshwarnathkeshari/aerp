"""
backend/tools/github_tool.py

GitHub integration — fetches all PR data needed by agents.

DESIGN PRINCIPLE: Tool vs MCP
  We use PyGitHub (direct API) instead of the GitHub MCP server because:
  1. More control over error handling and retry logic
  2. Easier to understand for learning
  3. No extra process to manage
  4. LangChain Tools wrap these functions for use by agents

WHAT IS A LANGCHAIN TOOL?
  A Tool is a function that an LLM agent can CHOOSE to call.
  You decorate a function with @tool and LangChain:
  1. Reads the function signature and docstring
  2. Describes the tool to the LLM
  3. Parses the LLM's arguments and calls your function
  4. Returns the result back to the LLM

  The LLM sees: "github_get_pr_diff(owner, repo, pr_number) -> Get the diff..."
  The LLM decides: "I need the diff. I'll call this tool."
"""

from github import Github, GithubException
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from backend.config.settings import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


def get_github_client(token: str) -> Github:
    """Returns an authenticated GitHub client."""
    return Github(token)


def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    """
    Parses a GitHub PR URL into (owner, repo, pr_number).

    Example:
      "https://github.com/myorg/myrepo/pull/42"
      → ("myorg", "myrepo", 42)
    """
    # Remove trailing slash and split
    parts = pr_url.rstrip("/").split("/")
    # URL format: https://github.com/{owner}/{repo}/pull/{number}
    pr_number = int(parts[-1])
    repo_name = parts[-3]
    owner = parts[-4]
    return owner, repo_name, pr_number


async def fetch_pr_data(pr_url: str, github_token: str) -> dict:
    """
    Fetches complete PR data from GitHub.
    This is called by the context_collector_node (not an LLM tool).
    Returns a PRMetadata-compatible dict.
    """
    owner, repo_name, pr_number = parse_pr_url(pr_url)
    logger.info("Fetching PR from GitHub", owner=owner, repo=repo_name, pr=pr_number)

    if owner == "fake":
        return {
            "pr_number": pr_number,
            "title": "Mock PR for Testing",
            "description": "This is a mock PR.",
            "author": "dev1",
            "branch": "feature/mock",
            "base_branch": "main",
            "repo_owner": owner,
            "repo_name": repo_name,
            "changed_files": ["backend/utils/llm_factory.py"],
            "diff": "--- a/backend/utils/llm_factory.py\n+++ b/backend/utils/llm_factory.py\n@@ -1,1 +1,2 @@\n-print('hello')\n+print('world')",
            "commit_messages": ["Initial commit"],
        }

    gh = get_github_client(github_token)
    repo = gh.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    # Get changed files
    changed_files = [f.filename for f in pr.get_files()]

    # Get full diff
    # Design Note: get the diff? Agents need to see exactly what changed line-by-line.
    # The diff is the primary input for Code Review, Security, and DB agents.
    import httpx

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            pr.diff_url,
            headers={"Authorization": f"token {github_token}"},
        )
        diff = response.text

    # Get commit messages
    commits = list(pr.get_commits())
    commit_messages = [c.commit.message for c in commits]

    return {
        "pr_number": pr_number,
        "title": pr.title,
        "description": pr.body or "",
        "author": pr.user.login,
        "branch": pr.head.ref,
        "base_branch": pr.base.ref,
        "repo_owner": owner,
        "repo_name": repo_name,
        "changed_files": changed_files,
        "diff": diff,
        "commit_messages": commit_messages,
    }


async def post_pr_comments(pr_url: str, findings: list, github_token: str) -> str:
    """
    Posts the final review findings as a general issue comment on the PR.
    """
    owner, repo_name, pr_number = parse_pr_url(pr_url)
    logger.info(
        "Posting review comments to GitHub", owner=owner, repo=repo_name, pr=pr_number
    )

    if owner == "fake":
        logger.info("Mock PR detected. Skipping actual GitHub API call.")
        return "https://github.com/fake/repo/pull/1#issuecomment-fake"
    gh = get_github_client(github_token)
    repo = gh.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    if not findings:
        body = "## AERP Code Review\n\n✅ Everything looks good! No major issues found."
    else:
        body = "## AERP Code Review Findings\n\n"
        for finding in findings:
            # We assume findings are instances of CodeFinding Pydantic models
            title = getattr(finding, "title", "Issue")
            severity = getattr(finding, "severity", "medium").upper()
            desc = getattr(finding, "description", "")
            file_path = getattr(finding, "file_path", "General")

            body += f"### [{severity}] {title}\n"
            body += f"**File:** `{file_path}`\n\n"
            body += f"{desc}\n\n"

            if hasattr(finding, "evidence") and finding.evidence:
                body += f"**Evidence:**\n```\n{finding.evidence}\n```\n\n"

    try:
        comment = pr.create_issue_comment(body)
        logger.info("Comment posted successfully", url=comment.html_url)
        return comment.html_url
    except GithubException as e:
        logger.error("Failed to post comment", error=str(e))
        return f"Error: {e.data}"


async def post_single_finding_comment(
    pr_url: str, finding: dict, github_token: str
) -> str:
    """
    Posts a single review finding to the PR.
    Attempts an inline review comment if file_path and line_number are available.
    Falls back to a general issue comment if the line is outside the PR diff.
    """
    owner, repo_name, pr_number = parse_pr_url(pr_url)
    logger.info(
        "Posting single finding to GitHub", owner=owner, repo=repo_name, pr=pr_number
    )

    if owner == "fake":
        logger.info("Mock PR detected. Skipping actual GitHub API call.")
        return "https://github.com/fake/repo/pull/1#issuecomment-fake"

    gh = get_github_client(github_token)
    repo = gh.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    # Use edited message if available, otherwise construct default
    if finding.get("edited_message"):
        body = finding["edited_message"]
    else:
        title = finding.get("title", "Issue")
        severity = finding.get("severity", "medium").upper()
        desc = finding.get("description", "")
        file_path = finding.get("file_path", "General")

        body = "## AERP AI Review Finding\n\n"
        body += f"### [{severity}] {title}\n"
        body += f"**File:** `{file_path}`\n\n"
        body += f"{desc}\n\n"

        if finding.get("evidence"):
            body += f"**Evidence:**\n```\n{finding['evidence']}\n```\n\n"

    # Try to post inline comment if file and line are provided
    file_path = finding.get("file_path")
    line_number = finding.get("line_number")

    if file_path and file_path != "General" and line_number:
        try:
            # get latest commit in the PR
            commits = pr.get_commits()
            latest_commit = commits.reversed[0]

            # create_review_comment using line (requires PyGithub >= 1.55)
            comment = pr.create_review_comment(
                body=body, commit=latest_commit, path=file_path, line=int(line_number)
            )
            logger.info(
                "Inline review comment posted successfully", url=comment.html_url
            )
            return comment.html_url
        except GithubException as e:
            # 422 usually means the line is not part of the PR diff
            logger.warning(
                "Failed to post inline comment (likely outside diff). Falling back to general issue comment.",
                error=str(e),
            )
            # Fall through to post as general issue comment

    # Fallback to general issue comment
    try:
        comment = pr.create_issue_comment(body)
        logger.info("General issue comment posted successfully", url=comment.html_url)
        return comment.html_url
    except GithubException as e:
        logger.error("Failed to post comment", error=str(e))
        return f"Error: {e.data}"


async def get_file_content(
    repo_owner: str, repo_name: str, file_path: str, branch: str, github_token: str
) -> str:
    """
    Fetches the raw content of a specific file from a GitHub repository.
    """
    if repo_owner == "fake":
        return f"# Mock content for {file_path}\ndef mock_func():\n    pass\n"

    gh = get_github_client(github_token)
    try:
        repo = gh.get_repo(f"{repo_owner}/{repo_name}")
        contents = repo.get_contents(file_path, ref=branch)
        # Contents can be a list if it's a directory, but we assume a single file
        return contents.decoded_content.decode("utf-8")
    except GithubException as e:
        logger.error("Failed to fetch file content", file_path=file_path, error=str(e))
        return ""


async def create_pull_request(
    repo_owner: str,
    repo_name: str,
    branch_name: str,
    base_branch: str,
    title: str,
    body: str,
    files: dict,
    github_token: str,
) -> str:
    """
    Creates a new branch, commits the given files, and opens a Pull Request.
    `files` is a dict of {filepath: content}
    """
    logger.info(
        "Creating new Pull Request",
        repo=f"{repo_owner}/{repo_name}",
        branch=branch_name,
    )
    if repo_owner == "fake":
        logger.info(
            "Mock PR detected. Skipping actual GitHub API call for PR creation."
        )
        return "https://github.com/fake/repo/pull/999"

    gh = get_github_client(github_token)
    try:
        repo = gh.get_repo(f"{repo_owner}/{repo_name}")

        # 1. Get base branch commit SHA
        base = repo.get_branch(base_branch)

        # 2. Create new branch
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base.commit.sha)

        # 3. Commit files
        for file_path, content in files.items():
            repo.create_file(
                path=file_path,
                message=f"Auto-generated {file_path}",
                content=content,
                branch=branch_name,
            )

        # 4. Open PR
        pr = repo.create_pull(
            title=title, body=body, head=branch_name, base=base_branch
        )
        logger.info("Pull Request created successfully", url=pr.html_url)
        return pr.html_url
    except GithubException as e:
        logger.error("Failed to create PR", error=str(e))
        return f"Error: {e.data}"


# ── LangChain Tools (for agent use) ──────────────────────────────────────────
# These tools are given to agents so they can fetch specific data on demand.


@tool
def github_get_file_content(
    owner: str,
    repo: str,
    file_path: str,
    ref: str = "main",
    *,
    config: RunnableConfig = None,
) -> str:
    """
    Fetch the full content of a specific file from a GitHub repository.
    Use when you need to see the complete file, not just the diff.

    Args:
        owner: Repository owner (e.g., "myorg")
        repo: Repository name (e.g., "myrepo")
        file_path: Path to the file (e.g., "src/services/payment.py")
        ref: Branch or commit SHA (default: "main")

    Returns:
        File content as a string, or error message.
    """
    try:
        token = config["configurable"].get("github_token") if config else None
        gh = get_github_client(token)
        repository = gh.get_repo(f"{owner}/{repo}")
        file_content = repository.get_contents(file_path, ref=ref)
        return file_content.decoded_content.decode("utf-8")
    except GithubException as e:
        return f"Error fetching file: {e.status} - {e.data}"


@tool
def github_search_code(
    owner: str, repo: str, query: str, *, config: RunnableConfig = None
) -> str:
    """
    Search for code patterns across a GitHub repository.
    Use to find usages of a function, class, or pattern across the codebase.

    Args:
        owner: Repository owner
        repo: Repository name
        query: Search term (e.g., "authenticate" or "process_payment")

    Returns:
        List of files containing the search term with snippets.
    """
    try:
        token = config["configurable"].get("github_token") if config else None
        gh = get_github_client(token)
        results = gh.search_code(f"{query} repo:{owner}/{repo}")
        items = list(results[:10])  # Limit to 10 results
        if not items:
            return f"No results found for '{query}'"

        output = [f"Found {results.totalCount} matches for '{query}':\n"]
        for item in items:
            output.append(f"📄 {item.path}")
        return "\n".join(output)
    except GithubException as e:
        return f"Search error: {e.status} - {e.data}"


@tool
def github_post_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    commit_id: str,
    path: str,
    position: int,
    *,
    config: RunnableConfig = None,
) -> str:
    """
    Post a review comment on a specific line of the GitHub PR.
    Used by the output phase to post findings directly on the PR.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        body: Comment text
        commit_id: The commit SHA the comment applies to
        path: File path for the comment
        position: Line position in the diff

    Returns:
        Comment URL or error message.
    """
    try:
        token = config["configurable"].get("github_token") if config else None
        gh = get_github_client(token)
        repository = gh.get_repo(f"{owner}/{repo}")
        pr = repository.get_pull(pr_number)
        commit = repository.get_commit(commit_id)
        comment = pr.create_review_comment(
            body=body,
            commit=commit,
            path=path,
            position=position,
        )
        return f"Comment posted: {comment.html_url}"
    except GithubException as e:
        return f"Error posting comment: {e.status} - {e.data}"
