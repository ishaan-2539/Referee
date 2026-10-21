# Referee — MCP Server for Informal Financial Agreements

> **"Alexa reminders remember *when*. Referee remembers *what you agreed*."**[cite: 3]

Referee is an MCP (Model Context Protocol) server engineered for Amazon Alexa+ and web platforms. It parses informal handshake deals, detects vague terms using a rule engine, asks structured clarifying questions, and provides deterministic verdicts over time[cite: 1, 3].

---

## 🌟 Key Features
- **Deterministic Vagueness Detection:** Identifies relative deadlines, pronoun counterparties, missing modes, and fuzzy amounts via the standalone `vagueterms` rule engine[cite: 1, 3].
- **Append-Only SQLite Ledger:** Preserves complete amendment and payment history[cite: 3].
- **Bedrock + Regex Parser:** Leverages Amazon Nova models on AWS Bedrock for entity parsing with an automated offline regex fallback[cite: 1, 3].
- **Streamable HTTP MCP Standard:** Built against MCP protocol specification `2025-11-25`[cite: 1, 3].
- **Live Simulator & Inspector Panel:** Includes an interactive web interface with speech recognition and live JSON-RPC traffic inspection.

---

## 🛠 Tech Stack
- **Language:** Python 3.11+[cite: 3]
- **MCP Framework:** `mcp` Official Python SDK[cite: 3]
- **Storage:** SQLite[cite: 3]
- **AI / Extraction:** Amazon Bedrock (Amazon Nova) + `dateutil`[cite: 3]
- **UI:** Vanilla JS, HTML5 Web Speech API, Tailwind CSS

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/your-username/referee.git
cd referee
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ../vagueterms
pip install -e .