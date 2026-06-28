"""
backend/models/findings.py

Design Note: Pydantic MODELS FOR LLM OUTPUT?
  When we call Gemini, we could get back free-form text like:
    "There's a bug on line 42. Also, the auth is broken."

  That's useless for a system. We need structured, reliable JSON.
  LangChain's `with_structured_output(model)` forces Gemini to return
  exactly the shape defined by a Pydantic model.

  If Gemini tries to return something that doesn't match, LangChain
  retries. If it still fails, it raises a clear exception.

HOW `with_structured_output` WORKS UNDER THE HOOD:
  1. LangChain converts the Pydantic model to a JSON Schema
  2. Passes the schema to Gemini as a "response_format" instruction
  3. Parses the response back into the Pydantic model
  4. You get a typed Python object, not a raw string

INTERVIEW QUESTION: "How do you prevent LLMs from hallucinating wrong formats?"
  Answer: Use structured output (function calling / tool calling mode).
  Gemini/GPT-4 has a mode where it MUST return valid JSON that matches
  a provided schema. This is called "constrained decoding" or "function calling".
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# Enums — constrain values the LLM can output
# ─────────────────────────────────────────────────────────────────────────────


class Severity(str, Enum):
    """
    Severity of a finding.

    Design Note: str + Enum
      - Enum: constrains LLM output to valid values only
      - str: makes it JSON-serializable without extra steps
      - The LLM literally cannot output "BLOCKER" or "WARNING" — only these values.
    """

    CRITICAL = "critical"  # Must fix before merge — security hole, data loss, crash
    HIGH = "high"  # Should fix — significant bug or vulnerability
    MEDIUM = "medium"  # Should consider — code quality, performance concern
    LOW = "low"  # Nice to fix — style, minor optimization
    INFO = "info"  # Informational — no action needed


class Recommendation(str, Enum):
    """Final recommendation from an agent."""

    APPROVE = "approve"  # Looks good, ship it
    APPROVE_WITH_COMMENTS = "approve_with_comments"  # Minor issues, but ok
    REQUEST_CHANGES = "request_changes"  # Issues that need fixing
    BLOCK = "block"  # Critical issues — do NOT merge


# ─────────────────────────────────────────────────────────────────────────────
# CodeFinding — a single issue found by an agent
# ─────────────────────────────────────────────────────────────────────────────


class CodeFinding(BaseModel):
    """
    A single issue found by an agent.

    DESIGN: Each finding is self-contained — it has everything needed to
    understand the problem and fix it, without looking at other findings.

    This is important because findings are posted individually as GitHub
    PR comments. Each comment must be understandable in isolation.
    """

    title: str = Field(
        description="Short, specific title of the issue. "
        "Example: 'SQL Injection in user search query'. "
        "Maximum 80 characters. Do NOT use generic titles like 'Bug found'."
    )

    severity: Severity = Field(
        description="How critical is this issue? "
        "critical=must fix, high=should fix, medium=consider fixing, "
        "low=minor, info=informational"
    )

    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Your confidence that this is a real issue, from 0.0 to 1.0. "
        "0.9+ = very certain. 0.5 = unsure. Be honest — "
        "low confidence findings won't be posted as PR comments.",
    )

    description: str = Field(
        description="Full explanation of the problem. Include: "
        "1) What the issue is, "
        "2) Why it's a problem, "
        "3) What could go wrong if not fixed. "
        "Write for a senior engineer who will review your comment."
    )

    file_path: Optional[str] = Field(
        default=None,
        description="File path where the issue is located. "
        "Example: 'backend/api/users.py'. "
        "None if the issue is general (not tied to a specific file).",
    )

    line_number: Optional[int] = Field(
        default=None,
        description="Line number of the issue within the file. "
        "None if you cannot determine the exact line.",
    )

    evidence: str = Field(
        default="Not provided.",
        description="The exact code snippet or pattern you observed that led to this finding. "
        "Quote the relevant lines. This is your proof.",
    )

    suggested_fix: Optional[str] = Field(
        default=None,
        description="How to fix this issue. Include a corrected code snippet if possible. "
        "Be specific and actionable. None if you cannot suggest a fix.",
    )

    owasp_category: Optional[str] = Field(
        default=None,
        description="For security findings only: the OWASP Top 10 category. "
        "Example: 'A03:2021 - Injection'. None for non-security findings.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# AgentReport — the complete output from one agent run
# ─────────────────────────────────────────────────────────────────────────────


class AgentReport(BaseModel):
    """
    The complete structured output from one agent.

    An agent returns ONE AgentReport containing MULTIPLE CodeFindings.
    This is the object that gets stored in ReviewState under
    `code_review_result`, `security_result`, etc.
    """

    findings: list[CodeFinding] = Field(
        description="List of all issues found. "
        "If the code looks clean, return an empty list — do NOT invent issues. "
        "Quality over quantity. 3 real findings beat 10 vague ones."
    )

    overall_assessment: str = Field(
        description="A 2-3 sentence summary of the overall code quality / security posture. "
        "Be direct and professional. "
        "Example: 'The authentication logic has a critical bypass vulnerability. "
        "The rest of the code follows good practices.'"
    )

    recommendation: Recommendation = Field(
        description="Your final recommendation for this PR."
    )

    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Your overall confidence in this review, from 0.0 to 1.0.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# ConsensusReport — the final unified output from the Consensus Agent
# ─────────────────────────────────────────────────────────────────────────────


class ConsensusReport(BaseModel):
    """
    The unified structured output from the Consensus Agent.

    It deduplicates findings from the 8 specialist agents and assigns
    a holistic risk score based on the entire picture.
    """

    final_findings: list[CodeFinding] = Field(
        description="Deduplicated and consolidated list of the most important findings. "
        "Filter out noise, combine duplicates, and resolve conflicting advice."
    )

    overall_assessment: str = Field(
        description="A holistic summary of the PR, synthesizing input from all specialist agents. "
        "Highlight the most critical areas of concern."
    )

    recommendation: Recommendation = Field(
        description="The final unified recommendation for this PR (approve, approve_with_comments, etc.)."
    )

    risk_score: int = Field(
        ge=0,
        le=100,
        description="Overall risk score from 0 to 100. "
        "0 = perfectly safe, no issues. "
        "100 = absolutely critical, must not be deployed. "
        "Calculate this intelligently based on the severity and impact of the final_findings.",
    )
