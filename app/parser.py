import re
from typing import Optional, Dict
from datetime import datetime


class MpesaParser:
    """Parse M-Pesa SMS messages and extract transaction details"""

    TRANSACTION_TYPES = {
        "SENT": ["you have sent", "sent to", "paid to", "transferred to"],
        "RECEIVED": ["you have received", "received from"],
        "WITHDRAWN": ["withdraw", "withdrawn from"],
        "BOUGHT": ["bought", "airtime for"],
        "BALANCE": ["balance was", "your balance is"],
        "REVERSED": ["reversed", "transaction reversed"],
        "PAYBILL": ["paid to", "for account"],
    }

    @staticmethod
    def extract_amount(message: str) -> Optional[float]:
        """Extract amount from M-Pesa message"""
        patterns = [
            r"Ksh\s*([\d,]+\.?\d*)",
            r"KES\s*([\d,]+\.?\d*)",
            r"amount\s+(?:of\s+)?Ksh\s*([\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None

    @staticmethod
    def extract_transaction_code(message: str) -> Optional[str]:
        """Extract transaction code (e.g., RK12AB34CD)"""
        pattern = r"\b([A-Z]{2}\d{2}[A-Z0-9]{5,6})\b"
        match = re.search(pattern, message)
        return match.group(1) if match else None

    @staticmethod
    def extract_balance(message: str) -> Optional[float]:
        """Extract new balance from message"""
        patterns = [
            r"balance (?:is|was)\s+Ksh\s*([\d,]+\.?\d*)",
            r"New.*?balance.*?Ksh\s*([\d,]+\.?\d*)",
            r"balance.*?Ksh\s*([\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                balance_str = match.group(1).replace(",", "")
                try:
                    return float(balance_str)
                except ValueError:
                    continue
        return None

    @staticmethod
    def extract_recipient(message: str) -> Optional[str]:
        """Extract recipient name or number"""
        patterns = [
            r"(?:sent to|paid to|received from)\s+([A-Z\s]+?)(?:\s+\d|\s+on|\s+Ksh|\.)",
            r"(?:sent to|paid to|received from)\s+(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def determine_transaction_type(cls, message: str) -> str:
        """Determine the type of M-Pesa transaction"""
        message_lower = message.lower()

        for trans_type, keywords in cls.TRANSACTION_TYPES.items():
            if any(keyword in message_lower for keyword in keywords):
                return trans_type

        return "UNKNOWN"

    @classmethod
    def parse(cls, sender: str, message: str) -> Dict:
        """Parse M-Pesa message and return structured data"""
        transaction_type = cls.determine_transaction_type(message)
        amount = cls.extract_amount(message)
        transaction_code = cls.extract_transaction_code(message)
        balance = cls.extract_balance(message)
        recipient = cls.extract_recipient(message)

        return {
            "sender": sender,
            "raw_message": message,
            "transaction_type": transaction_type,
            "amount": amount,
            "transaction_code": transaction_code,
            "balance": balance,
            "recipient": recipient,
            "timestamp": datetime.utcnow(),
            "parsed_successfully": amount is not None and transaction_code is not None,
        }


def test_parser():
    """Test the parser with sample M-Pesa messages"""
    test_messages = [
        "RK12AB34CD confirmed. You have sent Ksh500.00 to JOHN DOE. New M-PESA balance is Ksh1,234.56.",
        "RK98XY76ZW confirmed. You have received Ksh1,000.00 from JANE SMITH. Your balance is Ksh2,234.56.",
        "RM45CD67EF confirmed. Ksh200.00 withdrawn from M-PESA. Balance was Ksh2,034.56.",
    ]

    for msg in test_messages:
        result = MpesaParser.parse("MPESA", msg)
        print(f"\nMessage: {msg[:50]}...")
        print(f"Type: {result['transaction_type']}")
        print(f"Amount: Ksh{result['amount']}")
        print(f"Code: {result['transaction_code']}")
        print(f"Balance: Ksh{result['balance']}")


if __name__ == "__main__":
    test_parser()
