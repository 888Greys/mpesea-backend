from datetime import datetime, date
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import Transaction, DailyLimit
from app.config import get_settings

settings = get_settings()


class SpendingAgent:
    """Intelligent agent to track spending and generate insights"""

    def __init__(self, db: Session):
        self.db = db
        self.daily_limit = settings.daily_limit
        self.warning_threshold = settings.warning_threshold

    def get_today_date(self) -> str:
        """Get today's date as string"""
        return date.today().isoformat()

    def get_or_create_daily_limit(self) -> DailyLimit:
        """Get or create daily limit record for today"""
        today = self.get_today_date()
        daily_limit = self.db.query(DailyLimit).filter(DailyLimit.date == today).first()

        if not daily_limit:
            daily_limit = DailyLimit(
                date=today,
                limit_amount=self.daily_limit,
                spent_amount=0.0,
                transaction_count=0
            )
            self.db.add(daily_limit)
            self.db.commit()
            self.db.refresh(daily_limit)

        return daily_limit

    def calculate_today_spending(self) -> float:
        """Calculate total spending for today"""
        today_start = datetime.combine(date.today(), datetime.min.time())

        spent_transactions = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.transaction_type.in_(["SENT", "WITHDRAWN", "BOUGHT", "PAYBILL"]),
            Transaction.timestamp >= today_start
        ).scalar()

        return spent_transactions or 0.0

    def update_daily_limit(self, transaction_amount: float):
        """Update daily limit record with new transaction"""
        daily_limit = self.get_or_create_daily_limit()
        daily_limit.spent_amount = self.calculate_today_spending()
        daily_limit.transaction_count += 1
        daily_limit.updated_at = datetime.utcnow()
        self.db.commit()

    def check_spending_status(self) -> Dict:
        """Check current spending status against limit"""
        daily_limit = self.get_or_create_daily_limit()
        spent = daily_limit.spent_amount
        limit = daily_limit.limit_amount
        remaining = limit - spent
        percentage_used = (spent / limit) * 100 if limit > 0 else 0

        status = "SAFE"
        if percentage_used >= 100:
            status = "EXCEEDED"
        elif percentage_used >= (self.warning_threshold * 100):
            status = "WARNING"

        return {
            "date": daily_limit.date,
            "spent": spent,
            "limit": limit,
            "remaining": remaining,
            "percentage_used": round(percentage_used, 2),
            "status": status,
            "transaction_count": daily_limit.transaction_count
        }

    def generate_message(self, transaction: Dict, spending_status: Dict) -> str:
        """Generate intelligent message for Slack notification"""
        trans_type = transaction.get("transaction_type", "UNKNOWN")
        amount = transaction.get("amount", 0)
        recipient = transaction.get("recipient", "")
        
        spent = spending_status["spent"]
        limit = spending_status["limit"]
        remaining = spending_status["remaining"]
        percentage = spending_status["percentage_used"]
        status = spending_status["status"]

        # Build message based on transaction type
        if trans_type == "SENT":
            action = f"sent Ksh{amount:,.2f} to {recipient}" if recipient else f"sent Ksh{amount:,.2f}"
        elif trans_type == "WITHDRAWN":
            action = f"withdrew Ksh{amount:,.2f}"
        elif trans_type == "BOUGHT":
            action = f"bought airtime worth Ksh{amount:,.2f}"
        elif trans_type == "PAYBILL":
            action = f"paid Ksh{amount:,.2f} via Paybill"
        elif trans_type == "RECEIVED":
            return f"💰 You received Ksh{amount:,.2f}! Current balance updated."
        else:
            action = f"spent Ksh{amount:,.2f}"

        # Status-based messages
        if status == "EXCEEDED":
            emoji = "🚨"
            warning = f"\n*ALERT!* You've exceeded your daily limit by Ksh{abs(remaining):,.2f}!"
        elif status == "WARNING":
            emoji = "⚠️"
            warning = f"\nYou've used {percentage:.1f}% of your daily limit. Only Ksh{remaining:,.2f} remaining!"
        else:
            emoji = "✅"
            warning = f"\nYou have Ksh{remaining:,.2f} left for today ({percentage:.1f}% used)."

        message = f"{emoji} Yo Mathew! You just {action}.\n"
        message += f"\n📊 *Today's spending:* Ksh{spent:,.2f} / Ksh{limit:,.2f}"
        message += warning

        return message

    def should_notify(self, transaction_type: str) -> bool:
        """Determine if notification should be sent for this transaction type"""
        notify_types = ["SENT", "WITHDRAWN", "BOUGHT", "PAYBILL"]
        return transaction_type in notify_types

    def get_weekly_summary(self) -> Dict:
        """Generate weekly spending summary"""
        from datetime import timedelta
        
        week_ago = datetime.now() - timedelta(days=7)
        
        weekly_spent = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.transaction_type.in_(["SENT", "WITHDRAWN", "BOUGHT", "PAYBILL"]),
            Transaction.timestamp >= week_ago
        ).scalar() or 0.0

        weekly_received = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.transaction_type == "RECEIVED",
            Transaction.timestamp >= week_ago
        ).scalar() or 0.0

        transaction_count = self.db.query(func.count(Transaction.id)).filter(
            Transaction.timestamp >= week_ago
        ).scalar() or 0

        return {
            "total_spent": weekly_spent,
            "total_received": weekly_received,
            "net": weekly_received - weekly_spent,
            "transaction_count": transaction_count,
            "period": "Last 7 days"
        }
