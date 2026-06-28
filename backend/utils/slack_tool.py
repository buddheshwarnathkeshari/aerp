import os
import aiohttp
import structlog
from backend.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


async def send_slack_notification(review_id: str, pr_url: str, risk_score: int):
    """
    Sends a Slack notification when a review requires human approval.
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.info("SLACK_WEBHOOK_URL not set. Skipping Slack notification.")
        return

    payload = {
        "text": f"🚨 *High Risk PR Requires Review!* 🚨\n\n"
        f"*Review ID:* `{review_id}`\n"
        f"*PR:* <{pr_url}|View Pull Request>\n"
        f"*Risk Score:* {risk_score}/100\n\n"
        f"Please review the findings and approve or reject the PR."
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status != 200:
                    logger.error(
                        "Failed to send Slack notification", status=response.status
                    )
                else:
                    logger.info(
                        "Slack notification sent successfully", review_id=review_id
                    )
    except Exception as e:
        logger.error("Error sending Slack notification", error=str(e))
