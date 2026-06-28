import json
from backend.utils.llm_factory import get_llm
from backend.prompts.documentation import SYSTEM_PROMPT, build_human_message
from backend.tools.github_tool import get_file_content
from langchain_core.messages import SystemMessage, HumanMessage
import structlog

logger = structlog.get_logger()


async def generate_documentation(
    pr_metadata: dict, jira_ticket: dict, findings: list
) -> dict:
    """
    Generates inline documentation by reading raw files and inserting docstrings.
    Returns a dict mapping {file_path: updated_content}.
    """
    logger.info(
        "Generating inline documentation for PR", pr_title=pr_metadata.get("title")
    )

    # 1. Fetch raw files
    repo_owner = pr_metadata.get("repo_owner")
    repo_name = pr_metadata.get("repo_name")
    branch = pr_metadata.get("branch", "main")
    changed_files = pr_metadata.get("changed_files", [])

    raw_files = {}
    for file_path in changed_files:
        # We skip non-code files
        if not file_path.endswith((".py", ".js", ".ts", ".go", ".java", ".md")):
            continue
        content = await get_file_content(repo_owner, repo_name, file_path, branch)
        if content:
            raw_files[file_path] = content

    # Also fetch README.md just in case it needs updating
    readme_content = await get_file_content(repo_owner, repo_name, "README.md", branch)
    if readme_content:
        raw_files["README.md"] = readme_content

    # 2. Ask LLM to document them
    llm = get_llm(temperature=0.2)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=build_human_message(pr_metadata, jira_ticket, findings, raw_files)
        ),
    ]

    response = await llm.ainvoke(messages)

    # 3. Parse JSON output
    content = response.content

    # Extract just the JSON array part
    start_idx = content.find("[")
    end_idx = content.rfind("]")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        content = content[start_idx : end_idx + 1]

    updated_files = {}
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            for item in parsed:
                path = item.get("file_path")
                body = item.get("content")
                if path and body:
                    updated_files[path] = body
        logger.info(
            "Successfully parsed inline documentation", num_files=len(updated_files)
        )
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse JSON from documentation agent",
            error=str(e),
            response=content,
        )

    return updated_files
