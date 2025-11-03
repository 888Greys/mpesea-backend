#!/usr/bin/env python3
"""
Simple script to run the M-Pesa tracker backend server
"""
import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    
    print("🚀 Starting M-Pesa Spending Tracker Backend...")
    print(f"📡 Server: http://{settings.host}:{settings.port}")
    print(f"📊 Daily Limit: Ksh{settings.daily_limit:,.2f}")
    print(f"💬 Slack: {'Configured' if settings.slack_webhook_url else 'Not configured'}")
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development",
        log_level="info"
    )
