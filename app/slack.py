import httpx
from app.config import get_settings
from typing import Optional

settings = get_settings()


async def send_slack_notification(message: str) -> bool:
    """Send notification to Slack via webhook"""
    if not settings.slack_webhook_url:
        print("⚠️ Slack webhook URL not configured")
        return False

    payload = {
        "text": message,
        "username": "M-Pesa Tracker",
        "icon_emoji": ":money_with_wings:"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                settings.slack_webhook_url,
                json=payload
            )
            
            if response.status_code == 200:
                print(f"✅ Slack notification sent successfully")
                return True
            else:
                print(f"❌ Slack notification failed: {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ Error sending Slack notification: {str(e)}")
        return False


async def send_test_message() -> bool:
    """Send a test message to Slack"""
    test_message = "🧪 Test message from M-Pesa Tracker!\n\nIf you see this, the integration is working perfectly."
    return await send_slack_notification(test_message)
