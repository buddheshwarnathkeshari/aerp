import ast
from backend.utils.llm_factory import get_llm
from backend.prompts.test import SYSTEM_PROMPT, build_human_message
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import structlog

logger = structlog.get_logger()


async def generate_tests(pr_metadata: dict, jira_ticket: dict) -> str:
    """
    Generates test code for an approved PR, with a built-in static syntax verification loop.
    """
    logger.info("Generating tests for PR", pr_title=pr_metadata.get("title"))

    llm = get_llm(temperature=0.2)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=build_human_message(pr_metadata, jira_ticket)),
    ]

    max_retries = 3
    for attempt in range(max_retries):
        logger.info("Test generation attempt", attempt=attempt + 1)
        response = await llm.ainvoke(messages)

        # Extract code
        code_content = response.content
        if code_content.startswith("```python"):
            code_content = (
                code_content.removeprefix("```python").removesuffix("```").strip()
            )
        elif code_content.startswith("```"):
            code_content = code_content.removeprefix("```").removesuffix("```").strip()

        # Static Verification Loop (Syntax Check)
        try:
            ast.parse(code_content)
            logger.info("Test code passed static syntax verification")
            return code_content
        except SyntaxError as e:
            logger.warning(
                "Syntax error in generated test code", error=str(e), line=e.lineno
            )

            # Append history and ask for fix
            messages.append(AIMessage(content=response.content))
            messages.append(
                HumanMessage(
                    content=f"The code you generated has a SyntaxError: {e} at line {e.lineno}. Please fix it and return ONLY the corrected python code."
                )
            )

    logger.error("Failed to generate valid test code after max retries")
    # Return best effort
    return code_content
