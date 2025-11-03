from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.database import get_db, init_db, Transaction
from app.parser import MpesaParser
from app.agent import SpendingAgent
from app.slack import send_slack_notification, send_test_message
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="M-Pesa Spending Tracker",
    description="Backend API for tracking M-Pesa transactions and managing spending limits",
    version="1.0.0"
)


class SmsPayload(BaseModel):
    sender: str
    message: str
    timestamp: int


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("✅ Database initialized")
    print(f"📊 Daily spending limit: Ksh{settings.daily_limit:,.2f}")
    print(f"⚠️  Warning threshold: {settings.warning_threshold * 100}%")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "M-Pesa Spending Tracker",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/webhook/sms")
async def receive_sms(payload: SmsPayload, db: Session = Depends(get_db)):
    """
    Receive SMS from Android app, parse M-Pesa transaction, 
    update database, and send Slack notification
    """
    try:
        print(f"\n📱 Received SMS from: {payload.sender}")
        print(f"📄 Message: {payload.message[:100]}...")

        # Handle test messages from Android app
        if payload.sender == "TEST" or "test" in payload.message.lower():
            print("🧪 Test message detected - sending Slack notification")
            test_message = "🧪 **Test Message Received!**\n\n✅ Your M-Pesa tracker is working perfectly!\n\nThe app can now forward SMS to the backend, and you'll get notifications for real M-Pesa transactions."
            await send_slack_notification(test_message)
            return JSONResponse(
                status_code=200,
                content={"status": "success", "message": "Test notification sent to Slack"}
            )

        # Parse M-Pesa message
        parsed = MpesaParser.parse(payload.sender, payload.message)
        
        if not parsed["parsed_successfully"]:
            print("⚠️ Failed to parse M-Pesa message")
            return JSONResponse(
                status_code=200,
                content={"status": "received", "parsed": False, "reason": "Could not extract transaction details"}
            )

        # Check if transaction already exists
        existing = db.query(Transaction).filter(
            Transaction.transaction_code == parsed["transaction_code"]
        ).first()

        if existing:
            print(f"⚠️ Duplicate transaction: {parsed['transaction_code']}")
            return JSONResponse(
                status_code=200,
                content={"status": "duplicate", "transaction_code": parsed["transaction_code"]}
            )

        # Save transaction to database
        transaction = Transaction(
            transaction_code=parsed["transaction_code"],
            transaction_type=parsed["transaction_type"],
            amount=parsed["amount"],
            recipient=parsed["recipient"],
            balance=parsed["balance"],
            raw_message=parsed["raw_message"],
            sender=parsed["sender"],
            processed=False
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        print(f"✅ Transaction saved: {parsed['transaction_code']} - {parsed['transaction_type']} Ksh{parsed['amount']}")

        # Initialize spending agent
        agent = SpendingAgent(db)
        
        # Update daily spending if it's an outgoing transaction
        if parsed["transaction_type"] in ["SENT", "WITHDRAWN", "BOUGHT", "PAYBILL"]:
            agent.update_daily_limit(parsed["amount"])

        # Get spending status
        spending_status = agent.check_spending_status()
        
        # Generate intelligent message
        message = agent.generate_message(parsed, spending_status)

        # Send Slack notification if configured
        if agent.should_notify(parsed["transaction_type"]):
            await send_slack_notification(message)

        # Mark transaction as processed
        transaction.processed = True
        db.commit()

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "transaction_code": parsed["transaction_code"],
                "transaction_type": parsed["transaction_type"],
                "amount": parsed["amount"],
                "spending_status": spending_status,
                "notification_sent": settings.slack_webhook_url != ""
            }
        )

    except Exception as e:
        print(f"❌ Error processing SMS: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_spending_status(db: Session = Depends(get_db)):
    """Get current spending status"""
    agent = SpendingAgent(db)
    status = agent.check_spending_status()
    return status


@app.get("/summary/weekly")
async def get_weekly_summary(db: Session = Depends(get_db)):
    """Get weekly spending summary"""
    agent = SpendingAgent(db)
    summary = agent.get_weekly_summary()
    return summary


@app.get("/transactions")
async def get_transactions(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent transactions"""
    transactions = db.query(Transaction).order_by(
        Transaction.timestamp.desc()
    ).limit(limit).all()
    
    return [
        {
            "id": t.id,
            "code": t.transaction_code,
            "type": t.transaction_type,
            "amount": t.amount,
            "recipient": t.recipient,
            "balance": t.balance,
            "timestamp": t.timestamp.isoformat(),
        }
        for t in transactions
    ]


@app.post("/test/slack")
async def test_slack():
    """Test Slack integration"""
    if not settings.slack_webhook_url:
        raise HTTPException(status_code=400, detail="Slack webhook URL not configured")
    
    success = await send_test_message()
    
    if success:
        return {"status": "success", "message": "Test message sent to Slack"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test message")


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "running",
        "database": db_status,
        "slack_configured": settings.slack_webhook_url != "",
        "daily_limit": settings.daily_limit,
        "environment": settings.environment
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development"
    )
