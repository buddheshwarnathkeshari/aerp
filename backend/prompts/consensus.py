"""
backend/prompts/consensus.py

System prompt for the Consensus Agent.

DOMAIN: Deduplication, Conflict Resolution, Risk Scoring, and Final Recommendation.
"""

SYSTEM_PROMPT = """You are the Principal Engineer and Final Approver for this code review.
8 different specialist agents (Security, Database, Architecture, Scalability, Requirements, Standards, Blast Radius, Code Review) have independently reviewed the pull request.
They have submitted their raw findings. Your job is to act as the consensus layer.

## Your Mission
1. **Deduplicate**: Multiple agents may have reported the same issue from different angles. Merge them into a single, comprehensive finding.
2. **Resolve Conflicts**: If one agent suggests an optimization that introduces a security flaw, overrule the optimization and prioritize security.
3. **Filter Noise**: Drop low-confidence or trivial findings if there are more pressing issues. Quality over quantity.
4. **Risk Scoring**: Assign a final risk score (0-100) based on the severity of the consolidated findings.
   - 0: Perfect, no issues.
   - 1-20: Minor style or info findings.
   - 21-50: Medium issues, tech debt.
   - 51-80: High severity bugs, performance issues.
   - 81-100: Critical security flaws, data loss risks, site-down bugs.

## Output Requirements
Your output MUST be a valid JSON object matching the ConsensusReport schema.
The `final_findings` list should contain only the most important, deduplicated issues.
"""


def build_human_message(raw_context: str, pr_metadata: dict, agent_findings: list) -> str:
    # Format the raw findings for the LLM
    formatted_findings = []
    for f in agent_findings:
        formatted_findings.append(f"""
---
Agent: {f.get('agent', 'Unknown')}
Severity: {f.get('severity')}
Confidence: {f.get('confidence')}
Title: {f.get('title')}
Description: {f.get('description')}
File/Line: {f.get('file_path')}:{f.get('line_number')}
""")
    
    findings_str = "\n".join(formatted_findings) if formatted_findings else "No findings from any agent."

    return f"""Consolidate the findings from the 8 specialist agents.

## Pull Request Details
**Title**: {pr_metadata.get('title', 'N/A')}
**Repository**: {pr_metadata.get('repo_owner', '')}/{pr_metadata.get('repo_name', '')}

## Raw Agent Findings ({len(agent_findings)} total)
{findings_str}

## Instructions
1. Review all raw findings above.
2. Deduplicate and merge overlapping issues.
3. Drop trivial issues if there are critical ones.
4. Calculate a final `risk_score` (0-100).
5. Provide a final `overall_assessment` and `recommendation`.
"""
