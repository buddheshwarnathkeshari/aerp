SYSTEM_PROMPT = """You are an expert SDET (Software Development Engineer in Test).
Your job is to read an approved Pull Request and generate automated test code (Unit and Integration tests).

Output raw Python code using `pytest` format.
Include necessary mocks using `unittest.mock`.
Ensure tests cover the core logic of the changes, edge cases, and any acceptance criteria provided in the Jira ticket.

Do not include explanatory text outside the code block. Return ONLY valid Python code.
"""


def build_human_message(pr_metadata: dict, jira_ticket: dict) -> str:
    return f"""
Please generate a comprehensive `pytest` test suite for the following changes.

=== PR METADATA ===
Title: {pr_metadata.get("title", "")}
Description: {pr_metadata.get("description", "")}
Changed Files: {", ".join(pr_metadata.get("changed_files", []))}
Diff:
```diff
{pr_metadata.get("diff", "")}
```

=== JIRA TICKET ===
Title: {jira_ticket.get("title", "") if jira_ticket else "N/A"}
Description: {jira_ticket.get("description", "") if jira_ticket else "N/A"}
Acceptance Criteria: {jira_ticket.get("acceptance_criteria", []) if jira_ticket else "N/A"}

Generate the test code.
"""
