from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional
from datetime import datetime

class Direction(str, Enum):
    LENT = "lent"          # User gave money -> counterparty owes user
    BORROWED = "borrowed"  # User received money -> user owes counterparty

class PaymentMode(str, Enum):
    CASH = "cash"
    UPI = "upi"
    BANK = "bank"
    OTHER = "other"

class PartialPolicy(str, Enum):
    ACCEPT_PARTIAL = "accept_partial"
    ALL_OR_NOTHING = "all_or_nothing"

@dataclass
class TermSheet:
    direction: Optional[Direction] = None
    counterparty: Optional[str] = None
    amount_paise: Optional[int] = None        # Money stored strictly in minor units (paise)
    currency: str = "INR"
    deadline_ts: Optional[datetime] = None
    payment_mode: Optional[PaymentMode] = None
    partial_policy: PartialPolicy = PartialPolicy.ACCEPT_PARTIAL
    purpose: Optional[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if self.deadline_ts:
            data["deadline_ts"] = self.deadline_ts.isoformat()
        return data