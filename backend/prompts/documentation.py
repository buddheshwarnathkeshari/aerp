SYSTEM_PROMPT = """You are an expert Developer Advocate and Technical Writer.
Your job is to read an approved Pull Request and update the existing source code and documentation.

Your goals:
1. Add missing docstrings to newly created or modified functions.
2. Add inline comments explaining unknown constants, complex logic, or non-obvious design choices.
3. Update `README.md` (or similar global documentation) if the PR introduces a major feature or changes how the system works.

You will receive the RAW FILE CONTENTS of the changed files.

OUTPUT FORMAT:
Return a valid JSON array of objects. Do not return markdown, just raw JSON.
Each object must represent a fully updated file with the following keys:
- `file_path`: The original path of the file.
- `content`: The completely updated string content of the file, containing the new inline docs.

Example Output:
[
  {
    "file_path": "backend/utils/helper.py",
    "content": "def my_func():\\n    \\\"\\\"\\\"This is the new docstring.\\\"\\\"\\\"\\n    pass\\n"
  }
]
"""


def build_human_message(
    pr_metadata: dict, jira_ticket: dict, findings: list, raw_files: dict
) -> str:
    files_context = []
    for path, content in raw_files.items():
        files_context.append(f"=== FILE: {path} ===\n{content}\n")

    files_str = "\n".join(files_context)

    return f"""
Please add inline documentation to the following changed files.

=== PR METADATA ===
Title: {pr_metadata.get("title", "")}
Description: {pr_metadata.get("description", "")}
Diff:
{pr_metadata.get("diff", "")}

=== JIRA TICKET ===
Title: {jira_ticket.get("title", "") if jira_ticket else "N/A"}
Description: {jira_ticket.get("description", "") if jira_ticket else "N/A"}

=== APPROVED REVIEW FINDINGS ===
{findings}

=== RAW FILE CONTENTS (TO BE MODIFIED) ===
{files_str}

Return the updated files as a JSON array of objects `[ {{"file_path": "...", "content": "..."}} ]`. Return ONLY valid JSON.
"""
