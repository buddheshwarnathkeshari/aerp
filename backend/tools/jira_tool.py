"""
backend/tools/jira_tool.py

Jira integration — fetches ticket data for the Requirements Agent.
"""

from jira import JIRA, JIRAError
from langchain_core.tools import tool
from backend.config.settings import get_settings
import re
import structlog

logger = structlog.get_logger()
settings = get_settings()


def get_jira_client() -> JIRA:
    """Returns an authenticated Jira client."""
    return JIRA(
        server=settings.jira_server,
        basic_auth=(settings.jira_email, settings.jira_api_token),
    )


def parse_jira_url(jira_url: str) -> str:
    """
    Parses a Jira URL to extract the ticket key.

    Examples:
      "https://mycompany.atlassian.net/browse/PROJ-123" → "PROJ-123"
      "PROJ-123" → "PROJ-123" (already a key)
    """
    # If it looks like a key already (e.g., PROJ-123), return as-is
    if re.match(r"^[A-Z]+-\d+$", jira_url.strip()):
        return jira_url.strip()

    # Extract from URL
    match = re.search(r"/browse/([A-Z]+-\d+)", jira_url)
    if match:
        return match.group(1)

    raise ValueError(f"Cannot parse Jira ticket key from: {jira_url}")


async def fetch_jira_ticket(jira_url: str) -> dict:
    """
    Fetches complete ticket data from Jira.
    Called by context_collector_node.
    Returns a JiraTicket-compatible dict.
    """
    ticket_key = parse_jira_url(jira_url)
    logger.info("Fetching Jira ticket", ticket=ticket_key)

    jira = get_jira_client()
    issue = jira.issue(ticket_key)

    # Parse acceptance criteria from description
    # Many teams write ACs in a specific format — we try to extract them
    description = issue.fields.description or ""
    acceptance_criteria = _extract_acceptance_criteria(description)

    return {
        "ticket_id": ticket_key,
        "title": issue.fields.summary,
        "description": description,
        "acceptance_criteria": acceptance_criteria,
        "business_rules": [],  # Could be extracted from custom fields
        "story_points": getattr(issue.fields, "story_points", None),
        "priority": issue.fields.priority.name if issue.fields.priority else "Medium",
        "status": issue.fields.status.name,
        "reporter": issue.fields.reporter.displayName
        if issue.fields.reporter
        else "Unknown",
        "linked_tickets": _get_linked_tickets(issue),
    }


def _extract_acceptance_criteria(description: str) -> list[str]:
    """
    Attempts to extract acceptance criteria from ticket description.
    Looks for common patterns teams use:
      - "Acceptance Criteria:" section header
      - Lines starting with "AC:" or "Given/When/Then"
      - Numbered/bulleted lists after AC header
    """
    criteria = []

    # Pattern 1: "Acceptance Criteria" section header
    ac_section_match = re.search(
        r"(?:Acceptance Criteria|AC|ACs)[:\s]*\n(.*?)(?:\n\n|\Z)",
        description,
        re.IGNORECASE | re.DOTALL,
    )
    if ac_section_match:
        section = ac_section_match.group(1)
        # Extract bullet points
        for line in section.split("\n"):
            line = line.strip().lstrip("*-•·").strip()
            if line and len(line) > 10:  # Filter empty/very short lines
                criteria.append(line)

    # Pattern 2: Given/When/Then format
    gwt_matches = re.findall(r"(?:Given|When|Then).*", description, re.IGNORECASE)
    for match in gwt_matches:
        if match not in criteria:
            criteria.append(match.strip())

    return (
        criteria if criteria else ["No structured acceptance criteria found in ticket"]
    )


def _get_linked_tickets(issue) -> list[str]:
    """Extracts linked ticket keys."""
    linked = []
    if hasattr(issue.fields, "issuelinks"):
        for link in issue.fields.issuelinks:
            if hasattr(link, "outwardIssue"):
                linked.append(link.outwardIssue.key)
            elif hasattr(link, "inwardIssue"):
                linked.append(link.inwardIssue.key)
    return linked


# ── LangChain Tool (for Requirements Agent) ────────────────────────────────


@tool
def jira_get_ticket_details(ticket_key: str) -> str:
    """
    Fetch detailed information about a Jira ticket including acceptance criteria.
    Use when you need to verify if the code implementation matches requirements.

    Args:
        ticket_key: Jira ticket key (e.g., "PROJ-123")

    Returns:
        Formatted ticket details including acceptance criteria.
    """
    try:
        jira = get_jira_client()
        issue = jira.issue(ticket_key)
        description = issue.fields.description or "No description"
        criteria = _extract_acceptance_criteria(description)

        output = f"""
JIRA TICKET: {ticket_key}
Title: {issue.fields.summary}
Status: {issue.fields.status.name}
Priority: {issue.fields.priority.name if issue.fields.priority else "N/A"}

DESCRIPTION:
{description[:2000]}  

ACCEPTANCE CRITERIA:
{chr(10).join(f"  {i + 1}. {c}" for i, c in enumerate(criteria))}
"""
        return output.strip()
    except JIRAError as e:
        return f"Error fetching Jira ticket: {e.status_code} - {e.text}"
