import os
import urllib.parse
from typing import Optional, Dict, Any

def generate_upi_link(
    amount_inr: float,
    payee_vpa: Optional[str] = None,
    payee_name: str = "Referee",
    note: str = "Referee Settlement"
) -> Optional[str]:
    """Generates a standard upi://pay URI if payee_vpa is available in env or passed explicitly."""
    vpa = payee_vpa or os.getenv("PAYEE_VPA")
    if not vpa:
        return None

    params = {
        "pa": vpa,
        "pn": payee_name,
        "am": f"{amount_inr:.2f}",
        "cu": "INR",
        "tn": note
    }
    return f"upi://pay?{urllib.parse.urlencode(params)}"

def generate_whatsapp_share_link(deal_summary: str) -> str:
    """Generates a wa.me sharing link for counterparty confirmation."""
    text = f"Referee Agreement:\n{deal_summary}"
    encoded_text = urllib.parse.quote(text)
    return f"https://wa.me/?text={encoded_text}"