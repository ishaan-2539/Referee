This file is a merged representation of the entire codebase, combined into a single document by Repomix.

<file_summary>
This section contains a summary of this file.

<purpose>
This file contains a packed representation of the entire repository's contents.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.
</purpose>

<file_format>
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  - File path as an attribute
  - Full contents of the file
</file_format>

<usage_guidelines>
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.
</usage_guidelines>

<notes>
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)
</notes>

</file_summary>

<directory_structure>
Referee/
  docs/
    ARCHITECTURE.md
  src/
    referee/
      simulator/
        app.js
        index.html
      __init__.py
      links.py
      models.py
      parser.py
      seed.py
      server.py
      store.py
      verdict.py
  tests/
    test_extras.py
    test_parser.py
    test_server.py
    test_simulator.py
    test_store.py
    test_tools.py
    test_verdict.py
  .env.example
  .gitignore
  FRICTION_NOTES.md
  LICENSE
  pyproject.toml
  README.md
  Referee_Project_Overview.md
  referee.db
  ROADMAP.md
  test_tools.db
vagueterms/
  src/
    vagueterms/
      __init__.py
      detector.py
    vagueterms.egg-info/
      dependency_links.txt
      PKG-INFO
      requires.txt
      SOURCES.txt
      top_level.txt
  tests/
    __init__.py
    test_detector.py
  .gitignore
  LICENSE
  pyproject.toml
  README.md
pytest.ini
referee.db
test_tools.db
</directory_structure>

<files>
This section contains the contents of the repository's files.

<file path="Referee/docs/ARCHITECTURE.md">
# Referee Architecture & System Design

## Overview
Referee is a self-hosted Model Context Protocol (MCP) server that provides financial agreement tracking for voice interfaces (Alexa+) and web environments.

                 ┌──────────────────────────────────────────┐
                 │          Alexa+ / Web Simulator          │
                 └────────────────────┬─────────────────────┘
                                      │ Streamable HTTP / MCP (2025-11-25)
                                      ▼
                 ┌──────────────────────────────────────────┐
                 │            Referee MCP Server            │
                 │         (Starlette + FastMCP)            │
                 └──────┬──────────────────────────┬────────┘
                        │                          │
          ┌─────────────▼────────────┐   ┌─────────▼────────────┐
          │  Parsing Engine          │   │  Vagueness Detector  │
          │  (Amazon Bedrock Nova +  │   │  (Pure Python        │
          │   Regex Fallback)        │   │   `vagueterms`)      │
          └──────────────────────────┘   └──────────────────────┘
                                                   │
                                         ┌─────────▼────────────┐
                                         │  Append-Only Event   │
                                         │  Store (SQLite)      │
                                         └─────────┬────────────┘
                                                   │
                                         ┌─────────▼────────────┐
                                         │  Verdict Engine      │
                                         │  (Deterministic)     │
                                         └──────────────────────┘

## Core Principles
1. **Model Parses, Rules Decide:** LLMs parse fuzzy utterances into slot structures. Deterministic rule engines evaluate vagueness and calculate verdicts.
2. **Append-Only Ledger:** Deal states are never overwritten. Every action (`created`, `term_set`, `locked`, `payment`, `amended`) appends a immutable event.
3. **Zero Network Dependencies on Core:** The vagueness detector and verdict engines are pure Python functions that operate offline without external APIs.
</file>

<file path="pytest.ini">
[pytest]
testpaths = Referee/tests vagueterms/tests
pythonpath = Referee/src vagueterms/src
</file>

<file path="Referee/src/referee/simulator/app.js">
let currentDealId = null;
let lastLockedDealId = null;
let lastCounterparty = null;
let rpcCounter = 0;

const chatHistory = document.getElementById("chatHistory");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const trafficLog = document.getElementById("trafficLog");
const rpcCount = document.getElementById("rpcCount");

function sendSample(text) {
  userInput.value = text;
  handleUserMessage(text);
}

function appendMessage(sender, text, verdictCard = null) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `msg ${sender}`;

  const textContainer = document.createElement("div");
  textContainer.innerHTML = text.replace(/\n/g, "<br>");
  msgDiv.appendChild(textContainer);

  if (verdictCard) {
    const card = document.createElement("div");
    card.className = `verdict-card ${verdictCard.colour}`;
    card.innerHTML = `
      <div class="verdict-header">
        <span>${verdictCard.counterparty}</span>
        <span class="status-pill">${verdictCard.status}</span>
      </div>
      <div class="verdict-body">
        <span>Balance: <strong>₹${(verdictCard.balance_paise / 100).toFixed(0)}</strong></span>
        <span>Overdue: <strong>${verdictCard.days_overdue} day(s)</strong></span>
      </div>
    `;
    msgDiv.appendChild(card);
  }

  chatHistory.appendChild(msgDiv);
  setTimeout(() => {
    chatHistory.scrollTop = chatHistory.scrollHeight;
  }, 50);
}

function logRPC(method, params, result) {
  rpcCounter++;
  rpcCount.innerText = `${rpcCounter} calls`;

  const reqId = Math.floor(Math.random() * 1000);
  const reqFrame = { jsonrpc: "2.0", id: reqId, method: `tools/call/${method}`, params };
  const resFrame = { jsonrpc: "2.0", id: reqId, result };

  const reqBlock = document.createElement("div");
  reqBlock.className = "rpc-block";
  reqBlock.innerHTML = `<div class="rpc-type rpc-req"><span>Request</span> <span>${method}</span></div>${JSON.stringify(reqFrame, null, 2)}`;

  const resBlock = document.createElement("div");
  resBlock.className = "rpc-block";
  resBlock.innerHTML = `<div class="rpc-type rpc-res"><span>Response</span></div>${JSON.stringify(resFrame, null, 2)}`;

  trafficLog.appendChild(reqBlock);
  trafficLog.appendChild(resBlock);
  setTimeout(() => {
    trafficLog.scrollTop = trafficLog.scrollHeight;
  }, 50);
}

async function callMCPTool(toolName, args) {
  try {
    const res = await fetch(`/api/tool/${toolName}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(args)
    });
    const data = await res.json();
    logRPC(toolName, args, data);
    return data;
  } catch (err) {
    console.error("Tool execution failed", err);
    return { error: "Network or Server error" };
  }
}

function extractName(text) {
  const ignore = new Set([
    "paid", "payed", "repaid", "received", "for", "deal", "rs", "inr", "rupees", "i", "lent",
    "borrowed", "he", "she", "verdict", "status", "did", "pay", "a", "the",
    "who", "owes", "me", "what", "how", "much", "does", "owe", "cancel", "nevermind",
    "sounds", "good", "yep", "yeah", "sure", "cool", "do", "it", "lock", "confirm", "now"
  ]);
  const words = text.replace(/[^a-zA-Z\s]/g, "").split(/\s+/);
  for (const w of words) {
    if (w.length > 1 && !ignore.has(w.toLowerCase())) {
      return w;
    }
  }
  return null;
}

async function handleUserMessage(text) {
  if (!text || !text.trim()) return;
  const trimmed = text.trim();
  appendMessage("user", trimmed);
  userInput.value = "";

  const lower = trimmed.toLowerCase();

  // Intent 0: Conversational Pleasantries & Acknowledgments (Prevents chitchat from triggering propose_deal)
  const isChitchat = /^(alright|all right|got it|cool|okay|ok|thanks|thank you|hi|hello|hey|bye|goodbye|it's done|its done|perfect|great|awesome)\b[\s.!]*$/i.test(trimmed);

  if (isChitchat) {
    if (lower.startsWith("hi") || lower.startsWith("hello") || lower.startsWith("hey")) {
      appendMessage("alexa", "Hello! I'm Referee. You can record a new deal, log a payment, or check your ledger anytime.");
    } else {
      appendMessage("alexa", "You got it! Let me know whenever you need anything else.");
    }
    return;
  }

  // Intent 1: Cancel / Reset active proposal flow
  if (lower.includes("cancel") || lower.includes("nevermind") || lower.includes("reset") || lower.includes("stop")) {
    currentDealId = null;
    appendMessage("alexa", "Cancelled active deal proposal. How else can I help?");
    return;
  }

  // Intent 2: General Ledger Query (Typo & Phrasing Tolerant)
  const isLedgerQuery = lower.includes("ledger") ||
                        /\bwho\s+owes\s+me\b/i.test(lower) ||
                        /\bwhat\s+do\s+i\s+owe\b/i.test(lower) ||
                        /\boverall\s+balance\b/i.test(lower);

  if (isLedgerQuery) {
    currentDealId = null; // Clear draft proposal context when querying ledger
    const res = await callMCPTool("get_ledger", {});
    appendMessage("alexa", res.summary);
    return;
  }

  // Intent 3: Specific Verdict / Balance Query
  const isVerdictQuery = lower.includes("verdict") ||
                         lower.includes("status") ||
                         /\bdid\s+.*\s+(pay|payed)\b/i.test(lower) ||
                         /\bhas\s+.*\s+paid\b/i.test(lower) ||
                         /\bhow\s+much\s+does\s+.*\s+owe\b/i.test(lower) ||
                         /\bwhat\s+does\s+.*\s+owe\b/i.test(lower) ||
                         /\bdoes\s+.*\s+owe\b/i.test(lower);

  if (isVerdictQuery) {
    currentDealId = null; // Clear draft proposal context when asking a verdict query
    const detectedName = extractName(trimmed);
    let args = {};

    if (detectedName) {
      args.counterparty = detectedName;
    } else if (lastLockedDealId) {
      args.deal_id = lastLockedDealId;
    } else if (lastCounterparty) {
      args.counterparty = lastCounterparty;
    }

    const res = await callMCPTool("get_verdict", args);
    if (res.verdict_card) {
      appendMessage("alexa", res.summary, res.verdict_card);
    } else {
      appendMessage("alexa", res.summary || `No active record found for ${detectedName || 'that query'}.`);
    }
    return;
  }

  // Intent 4: Lock / Confirm Deal
  if (lower.includes("lock") || lower.includes("confirm") || lower.includes("sounds good") || lower.includes("go ahead") || lower.includes("do it")) {
    const dealToLock = currentDealId || lastLockedDealId;
    if (dealToLock) {
      const res = await callMCPTool("lock_deal", { deal_id: dealToLock, confirm: true });
      if (res.error) {
        appendMessage("alexa", res.summary || res.error);
      } else {
        let linksText = `\n\nWhatsApp Share: ${res.whatsapp_share_link}`;
        linksText += res.upi_link ? `\nUPI Link: ${res.upi_link}` : `\nUPI Link: (Set PAYEE_VPA in .env to generate UPI links)`;
        appendMessage("alexa", `${res.summary}${linksText}`);
        lastLockedDealId = dealToLock;
        currentDealId = null;
      }
    } else {
      appendMessage("alexa", "There is no active deal to lock right now.");
    }
    return;
  }

  // Intent 5: Log Payment (Tolerates "paid", "payed", "repaid", "received", "sent")
  const isPaymentIntent = /\b(paid|payed|repaid|received|sent|transferred)\b/i.test(lower);
  if (isPaymentIntent) {
    currentDealId = null; // Clear draft deal proposal when logging a payment
    const numMatch = trimmed.match(/\d+/);
    const amount = numMatch ? parseFloat(numMatch[0]) : 0;
    const detectedName = extractName(trimmed) || lastCounterparty;

    const res = await callMCPTool("log_payment", {
      amount_inr: amount,
      counterparty: detectedName,
      deal_id: lastLockedDealId
    });
    appendMessage("alexa", res.summary);
    return;
  }

  // Intent 6: Answer Clarifying Question for Active Deal Proposal
  if (currentDealId) {
    const res = await callMCPTool("answer_question", { deal_id: currentDealId, answer: trimmed });
    if (res.updated_slots && res.updated_slots.counterparty) {
      lastCounterparty = res.updated_slots.counterparty;
    }
    appendMessage("alexa", res.read_back || res.summary);
    return;
  }

  // Intent 7: Propose New Handshake Deal (Fallback)
  const res = await callMCPTool("propose_deal", { utterance: trimmed });
  if (res.deal_id) {
    currentDealId = res.deal_id;
    if (res.slots && res.slots.counterparty) {
      lastCounterparty = res.slots.counterparty;
    }
    appendMessage("alexa", res.summary);
  } else {
    appendMessage("alexa", "I couldn't process that handshake deal. Could you rephrase?");
  }
}

sendBtn.addEventListener("click", () => handleUserMessage(userInput.value));
userInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") handleUserMessage(userInput.value);
});

if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;

  micBtn.addEventListener("click", () => {
    recognition.start();
    micBtn.classList.add("listening");
  });

  recognition.onresult = (event) => {
    micBtn.classList.remove("listening");
    const transcript = event.results[0][0].transcript;
    handleUserMessage(transcript);
  };

  recognition.onerror = () => micBtn.classList.remove("listening");
  recognition.onend = () => micBtn.classList.remove("listening");
} else {
  micBtn.disabled = true;
  micBtn.title = "Speech recognition not supported in this browser";
}
</file>

<file path="Referee/src/referee/simulator/index.html">
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Referee — Alexa+ MCP Simulator</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      /* Surfaces: one warm-charcoal family, stepped lighter by layer */
      --bg-page: #0b0b0e;
      --bg-card: #131317;
      --bg-raised: #1b1b21;
      --bg-field: #101014;
      --line: #26262e;

      /* Red family */
      --red: #e03a3e;
      --red-deep: #7d1119;
      --red-wine: #3a0f14;
      --rose: #f2a7a9;

      /* Text */
      --ink: #f2ebe6;
      --ink-2: #9b9299;
      --ink-3: #62595f;

      /* Status tones, muted to sit with the reds */
      --ok: #86d6a0;
      --warn: #f0c56a;

      --font-sans: 'Inter Tight', system-ui, -apple-system, sans-serif;
      --font-serif: 'Instrument Serif', Georgia, serif;
      --font-mono: 'JetBrains Mono', ui-monospace, monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; font-family: var(--font-sans); }

    html, body {
      height: 100%;
      width: 100%;
      overflow: hidden;
      background: var(--bg-page);
      color: var(--ink);
      -webkit-font-smoothing: antialiased;
    }

    body {
      display: grid;
      grid-template-rows: auto 1fr;
      gap: 18px;
      padding: 22px;
      height: 100vh;
    }

    /* ---------- Top bar ---------- */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 2px 6px;
    }

    .brand { display: flex; align-items: center; gap: 14px; }

    .logo {
      width: 46px;
      height: 46px;
      border-radius: 50%;
      background: var(--red);
      display: grid;
      place-items: center;
      flex-shrink: 0;
    }
    .logo svg { width: 30px; height: 30px; color: var(--ink); }

    .brand-name {
      font-family: var(--font-serif);
      font-size: 2.1rem;
      line-height: 1;
      letter-spacing: -0.01em;
    }

    .header-right { display: flex; align-items: center; gap: 10px; }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      height: 36px;
      padding: 0 15px;
      border-radius: 999px;
      border: 1px solid var(--line);
      font-size: 0.78rem;
      font-weight: 500;
      color: var(--ink);
      background: var(--bg-card);
      white-space: nowrap;
    }
    .pill .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--red); }
    .pill.mono { font-family: var(--font-mono); font-size: 0.72rem; color: var(--ink-2); }

    /* ---------- Layout ---------- */
    .main-container {
      display: grid;
      grid-template-columns: 300px 1fr 400px;
      gap: 18px;
      min-height: 0;
    }

    .card {
      background: var(--bg-card);
      border: 1px solid var(--line);
      border-radius: 26px;
      display: flex;
      flex-direction: column;
      min-height: 0;
      overflow: hidden;
      position: relative;
    }

    .card-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding: 22px 24px 12px;
      flex-shrink: 0;
    }
    .card-title { font-family: var(--font-serif); font-size: 1.7rem; line-height: 1.1; letter-spacing: -0.01em; }
    .card-sub { font-size: 0.78rem; color: var(--ink-2); margin-top: 6px; }

    .round-btn {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      border: 1px solid var(--line);
      background: var(--bg-raised);
      display: grid;
      place-items: center;
      color: var(--ink);
      flex-shrink: 0;
    }
    .round-btn svg { width: 16px; height: 16px; }

    /* ---------- Brand panel ---------- */
    .hero {
      background: var(--red-wine);
      border-color: #4d161c;
      padding: 26px 24px 24px;
      justify-content: space-between;
    }

    .hero-top { position: relative; z-index: 2; }
    .eyebrow {
      font-size: 0.66rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--rose);
    }
    .hero h1 {
      font-family: var(--font-serif);
      font-weight: 400;
      font-size: 2.9rem;
      line-height: 0.98;
      letter-spacing: -0.015em;
      margin-top: 14px;
    }
    .hero h1 em { font-style: italic; color: var(--rose); }

    .hero-art { position: absolute; inset: 0; z-index: 1; pointer-events: none; }
    .orb {
      position: absolute;
      border-radius: 50%;
      background: radial-gradient(circle at 34% 30%, #ff6b6e 0%, #c9242b 38%, #5c0d14 78%, #2a070b 100%);
    }
    .orb.big { width: 330px; height: 330px; left: -70px; bottom: -120px; }
    .orb.small { width: 74px; height: 74px; right: 26px; top: 46%; }
    .ring {
      position: absolute;
      border-radius: 50%;
      border: 1px solid rgba(242, 167, 169, 0.22);
    }
    .ring.a { width: 360px; height: 360px; left: -30px; bottom: -80px; }
    .ring.b { width: 190px; height: 190px; right: -50px; top: 32%; }

    .hero-bottom { position: relative; z-index: 2; }
    .slots {
      list-style: none;
      font-size: 0.66rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      line-height: 1.9;
      color: var(--ink);
    }
    .slots-label { font-size: 0.62rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--rose); margin-bottom: 8px; }

    /* ---------- Chat ---------- */
    .chat-history {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 12px 24px 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .msg {
      max-width: 78%;
      padding: 13px 18px;
      border-radius: 22px;
      line-height: 1.5;
      font-size: 0.93rem;
      word-break: break-word;
    }

    .msg.user {
      align-self: flex-end;
      background: var(--red);
      color: #ffffff;
      border-bottom-right-radius: 6px;
      font-weight: 500;
    }

    .msg.alexa {
      align-self: flex-start;
      background: var(--bg-raised);
      border: 1px solid var(--line);
      color: var(--ink);
      border-bottom-left-radius: 6px;
    }
    .msg.alexa em { font-family: var(--font-serif); font-size: 1.05em; color: var(--rose); }

    /* Chips */
    .quick-prompts {
      padding: 4px 24px 14px;
      display: flex;
      gap: 8px;
      overflow-x: auto;
      flex-shrink: 0;
      scrollbar-width: none;
    }
    .quick-prompts::-webkit-scrollbar { display: none; }

    .chip {
      background: transparent;
      border: 1px solid var(--line);
      color: var(--ink-2);
      height: 36px;
      padding: 0 16px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 500;
      white-space: nowrap;
      cursor: pointer;
      transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
    }
    .chip:hover { background: var(--red-wine); border-color: var(--red-deep); color: var(--ink); }

    /* Verdict card */
    .verdict-card {
      margin-top: 12px;
      padding: 18px 18px 16px;
      border-radius: 18px;
      background: var(--bg-field);
      border: 1px solid var(--line);
      position: relative;
      overflow: hidden;
    }
    .verdict-card::before {
      content: "";
      position: absolute;
      inset: 0 0 auto 0;
      height: 5px;
      background: var(--rose);
    }
    .verdict-card.neutral::before { background: var(--rose); }
    .verdict-card.green::before { background: var(--ok); }
    .verdict-card.yellow::before { background: var(--warn); }
    .verdict-card.red::before { background: var(--red); }

    .verdict-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-family: var(--font-serif);
      font-size: 1.5rem;
      letter-spacing: -0.01em;
      margin: 4px 0 12px;
    }

    .status-pill {
      font-family: var(--font-sans);
      font-size: 0.64rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      padding: 5px 11px;
      border-radius: 999px;
      font-weight: 600;
      background: var(--red-wine);
      color: var(--rose);
    }
    .verdict-card.green .status-pill { background: var(--ok); color: #0d2216; }
    .verdict-card.yellow .status-pill { background: var(--warn); color: #2b1f05; }
    .verdict-card.red .status-pill { background: var(--red); color: #ffffff; }

    .verdict-body {
      font-size: 0.82rem;
      color: var(--ink-2);
      display: flex;
      gap: 24px;
    }
    .verdict-body strong { color: var(--ink); font-weight: 600; font-size: 1rem; margin-left: 4px; }

    /* Input */
    .input-area {
      padding: 0 24px 22px;
      display: flex;
      gap: 10px;
      align-items: center;
      flex-shrink: 0;
    }

    .input-area input {
      flex: 1;
      height: 52px;
      background: var(--bg-field);
      border: 1px solid var(--line);
      color: var(--ink);
      padding: 0 22px;
      border-radius: 999px;
      outline: none;
      font-size: 0.93rem;
      transition: border-color 0.15s ease;
    }
    .input-area input::placeholder { color: var(--ink-3); }
    .input-area input:focus { border-color: var(--red); }

    .btn {
      height: 52px;
      background: var(--red);
      color: #ffffff;
      border: none;
      padding: 0 28px;
      border-radius: 999px;
      font-weight: 600;
      cursor: pointer;
      font-size: 0.9rem;
      transition: background 0.15s ease;
    }
    .btn:hover { background: #ee5256; }

    .btn-mic {
      width: 52px;
      padding: 0;
      background: var(--bg-raised);
      border: 1px solid var(--line);
      color: var(--ink);
      display: grid;
      place-items: center;
    }
    .btn-mic:hover { background: var(--red-wine); }
    .btn-mic svg { width: 20px; height: 20px; }
    .btn-mic:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-mic.listening { background: var(--red); border-color: var(--red); animation: pulse 1s infinite; }

    @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.55; } 100% { opacity: 1; } }

    /* ---------- Inspector ---------- */
    .count-pill {
      display: inline-flex;
      align-items: center;
      height: 32px;
      padding: 0 13px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--bg-raised);
      font-size: 0.74rem;
      font-weight: 500;
      color: var(--ink);
      white-space: nowrap;
    }

    .traffic-log {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 8px 24px 20px;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .traffic-log:empty::before {
      content: "No calls yet. Tool traffic will appear here.";
      display: grid;
      place-items: center;
      flex: 1;
      border-radius: 18px;
      border: 1px dashed var(--line);
      color: var(--ink-3);
      font-family: var(--font-sans);
      font-size: 0.85rem;
      text-align: center;
      padding: 24px;
    }

    .rpc-block {
      background: var(--bg-field);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px 16px;
      white-space: pre-wrap;
      word-break: break-all;
      line-height: 1.45;
      color: var(--ink-2);
    }

    .rpc-type {
      font-weight: 500;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      font-size: 0.66rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }
    .rpc-req { color: var(--rose); }
    .rpc-res { color: var(--ok); }

    /* Segmented bar, echoes the reference */
    .segbar {
      display: flex;
      gap: 3px;
      margin: 0 24px 22px;
      height: 8px;
      flex-shrink: 0;
    }
    .segbar span { flex: 1; border-radius: 999px; }
    .segbar span:nth-child(1) { background: var(--red); flex: 3; }
    .segbar span:nth-child(2) { background: #b34a50; flex: 2; }
    .segbar span:nth-child(3) { background: var(--rose); flex: 1.5; }
    .segbar span:nth-child(4) { background: var(--ink); flex: 1; }

    /* Scrollbars */
    .chat-history, .traffic-log { scrollbar-width: thin; scrollbar-color: var(--line) transparent; }

    @media (max-width: 1240px) {
      .main-container { grid-template-columns: 1fr 380px; }
      .hero { display: none; }
    }
    @media (max-width: 900px) {
      html, body { overflow: auto; }
      body { height: auto; min-height: 100vh; padding: 14px; gap: 14px; }
      .main-container { grid-template-columns: 1fr; grid-template-rows: 78vh 360px; gap: 14px; }
      .header-right .pill.mono { display: none; }
      .msg { max-width: 90%; }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="logo" aria-label="Referee football logo">
        <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs><clipPath id="ball"><circle cx="20" cy="20" r="18.2"/></clipPath></defs>
          <circle cx="20" cy="20" r="18.2" stroke="currentColor" stroke-width="2.2"/>
          <g clip-path="url(#ball)" fill="currentColor">
            <polygon points="20,13.5 26.2,18 23.8,25.4 16.2,25.4 13.8,18"/>
            <polygon points="0,-6 5.7,-1.85 3.53,4.85 -3.53,4.85 -5.7,-1.85" transform="translate(31.2 4.6) rotate(36)"/>
            <polygon points="0,-6 5.7,-1.85 3.53,4.85 -3.53,4.85 -5.7,-1.85" transform="translate(38.1 25.9) rotate(108)"/>
            <polygon points="0,-6 5.7,-1.85 3.53,4.85 -3.53,4.85 -5.7,-1.85" transform="translate(20 39) rotate(180)"/>
            <polygon points="0,-6 5.7,-1.85 3.53,4.85 -3.53,4.85 -5.7,-1.85" transform="translate(1.9 25.9) rotate(252)"/>
            <polygon points="0,-6 5.7,-1.85 3.53,4.85 -3.53,4.85 -5.7,-1.85" transform="translate(8.8 4.6) rotate(324)"/>
          </g>
          <g stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
            <line x1="20" y1="13.5" x2="20" y2="7.5"/>
            <line x1="26.2" y1="18" x2="31.9" y2="16.1"/>
            <line x1="23.8" y1="25.4" x2="27.3" y2="30.3"/>
            <line x1="16.2" y1="25.4" x2="12.7" y2="30.3"/>
            <line x1="13.8" y1="18" x2="8.1" y2="16.1"/>
          </g>
        </svg>
      </div>
      <span class="brand-name">Referee</span>
    </div>
    <div class="header-right">
      <span class="pill mono">Spec 2025-11-25 · Streamable HTTP</span>
      <span class="pill"><span class="dot"></span>MCP server active</span>
    </div>
  </header>

  <div class="main-container">
    <!-- Brand panel -->
    <aside class="card hero">
      <div class="hero-art" aria-hidden="true">
        <div class="ring a"></div>
        <div class="ring b"></div>
        <div class="orb big"></div>
        <div class="orb small"></div>
      </div>
      <div class="hero-top">
        <div class="eyebrow">Handshake deals</div>
        <h1>Remember what you <em>agreed.</em></h1>
      </div>
      <div class="hero-bottom">
        <div class="slots-label">Terms we pin down</div>
        <ul class="slots">
          <li>Direction</li>
          <li>Counterparty</li>
          <li>Amount</li>
          <li>Deadline</li>
        </ul>
      </div>
    </aside>

    <!-- Chat -->
    <section class="card">
      <div class="card-head">
        <div>
          <div class="card-title">Alexa+ Simulator</div>
          <div class="card-sub">Speak or type a handshake deal</div>
        </div>
        <div class="round-btn" aria-hidden="true">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 8h12M9 3l5 5-5 5"/></svg>
        </div>
      </div>

      <div class="chat-history" id="chatHistory">
        <div class="msg alexa">
          Welcome! I am <strong>Referee</strong>. Say an agreement (e.g., <em>"I lent Aman 1500, he'll pay Friday"</em>) or query a verdict/ledger.
        </div>
      </div>

      <div class="quick-prompts">
        <button class="chip" onclick="sendSample('I lent Aman 1500, he\'ll pay Friday')">I lent Aman 1500...</button>
        <button class="chip" onclick="sendSample('Aman paid 500')">Aman paid 500</button>
        <button class="chip" onclick="sendSample('Did Aman pay?')">Did Aman pay?</button>
        <button class="chip" onclick="sendSample('Who owes me what?')">Who owes me what?</button>
      </div>

      <div class="input-area">
        <button class="btn btn-mic" id="micBtn" title="Voice input" aria-label="Voice input">
          <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="6" height="10" rx="3"/><path d="M4 9.5a6 6 0 0 0 12 0M10 15.5V18"/></svg>
        </button>
        <input type="text" id="userInput" placeholder="Speak or type a handshake deal..." />
        <button class="btn" id="sendBtn">Send</button>
      </div>
    </section>

    <!-- Inspector -->
    <section class="card">
      <div class="card-head">
        <div>
          <div class="card-title">MCP Traffic</div>
          <div class="card-sub">Raw JSON-RPC frames, live</div>
        </div>
        <span class="count-pill" id="rpcCount">0 calls</span>
      </div>
      <div class="traffic-log" id="trafficLog"></div>
      <div class="segbar" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
    </section>
  </div>

  <script src="/simulator/app.js"></script>
</body>
</html>
</file>

<file path="Referee/src/referee/__init__.py">

</file>

<file path="Referee/src/referee/links.py">
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
</file>

<file path="Referee/src/referee/models.py">
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
</file>

<file path="Referee/src/referee/parser.py">
import os
import re
import json
from datetime import datetime, timedelta, time
from typing import Optional, Tuple, Dict, Any
from dateutil.relativedelta import relativedelta, FR, MO, TU, WE, TH, SA, SU
from referee.models import TermSheet, Direction, PaymentMode

WEEKDAYS = {
    "monday": MO,
    "tuesday": TU,
    "wednesday": WE,
    "thursday": TH,
    "friday": FR,
    "saturday": SA,
    "sunday": SU
}

def parse_amount_paise(text: str) -> Optional[int]:
    """Extracts amount and converts Rupees to integer Paise."""
    text_lower = text.lower()
    
    k_match = re.search(r"\b(\d+(?:\.\d+)?)\s*k\b", text_lower)
    if k_match:
        return int(float(k_match.group(1)) * 1000 * 100)
        
    l_match = re.search(r"\b(\d+(?:\.\d+)?)\s*l\b", text_lower)
    if l_match:
        return int(float(l_match.group(1)) * 100000 * 100)

    num_match = re.search(r"\b(?:rs\.?|inr|\₹)?\s*(\d{1,3}(?:,\d{3})*|\d+)\b", text_lower)
    if num_match:
        raw_num = num_match.group(1).replace(",", "")
        return int(raw_num) * 100

    return None

def parse_direction_and_party(text: str) -> Tuple[Optional[Direction], Optional[str]]:
    """Extracts lending/borrowing direction and counterparty name."""
    text_lower = text.lower()

    is_lent = bool(re.search(r"\b(?:lent|loaned|gave|paid)\b", text_lower))
    is_borrowed = bool(re.search(r"\b(?:borrowed|took|got)\b", text_lower))

    from_match = re.search(r"\bfrom\s+([A-Za-z]+)", text, re.IGNORECASE)
    to_match = re.search(r"\bto\s+([A-Za-z]+)", text, re.IGNORECASE)

    party = None
    direction = None

    if is_borrowed:
        direction = Direction.BORROWED
        if from_match and from_match.group(1).lower() not in {"me", "a", "the", "some"}:
            party = from_match.group(1).capitalize()
        else:
            m = re.search(r"\b(?:borrowed|took|got)\s+(?:from\s+)?([A-Za-z]+)", text, re.IGNORECASE)
            if m and m.group(1).lower() not in {"from", "me", "a", "the", "some"}:
                party = m.group(1).capitalize()

    elif is_lent:
        direction = Direction.LENT
        if to_match and to_match.group(1).lower() not in {"me", "a", "the", "some"}:
            party = to_match.group(1).capitalize()
        else:
            m = re.search(r"\b(?:lent|loaned|gave|paid)\s+(?:to\s+)?([A-Za-z]+)", text, re.IGNORECASE)
            if m and m.group(1).lower() not in {"to", "me", "a", "the", "some"}:
                party = m.group(1).capitalize()

    if not direction and re.search(r"\b(he|she|they|him|her)\b", text_lower):
        if "pay" in text_lower or "owes" in text_lower:
            direction = Direction.LENT
            party = "he"

    return direction, party

def parse_deadline(text: str, base_dt: Optional[datetime] = None) -> Optional[datetime]:
    """Parses relative weekday deadlines into absolute datetimes (11:59 PM IST)."""
    text_lower = text.lower()
    now = base_dt or datetime.now()

    if "tomorrow" in text_lower:
        target = now + timedelta(days=1)
        return datetime.combine(target.date(), time(23, 59))

    for day_name, day_enum in WEEKDAYS.items():
        if day_name in text_lower:
            target = now + relativedelta(weekday=day_enum(+1))
            return datetime.combine(target.date(), time(23, 59))

    return None

def parse_payment_mode(text: str) -> Optional[PaymentMode]:
    """Detects specified payment mode."""
    text_lower = text.lower()
    if "upi" in text_lower or "gpay" in text_lower or "phonepe" in text_lower:
        return PaymentMode.UPI
    if "cash" in text_lower:
        return PaymentMode.CASH
    if "bank" in text_lower or "transfer" in text_lower:
        return PaymentMode.BANK
    return None

def parse_utterance_regex(utterance: str, base_dt: Optional[datetime] = None) -> TermSheet:
    """Regex + rule-based parser fallback."""
    direction, counterparty = parse_direction_and_party(utterance)
    amount_paise = parse_amount_paise(utterance)
    deadline_ts = parse_deadline(utterance, base_dt=base_dt)
    payment_mode = parse_payment_mode(utterance)

    return TermSheet(
        direction=direction,
        counterparty=counterparty,
        amount_paise=amount_paise,
        deadline_ts=deadline_ts,
        payment_mode=payment_mode
    )

def parse_utterance_bedrock(utterance: str, base_dt: Optional[datetime] = None) -> Optional[TermSheet]:
    """Parses utterance using Amazon Bedrock (Amazon Nova models). Returns None on failure."""
    try:
        import boto3
        region = os.getenv("AWS_REGION", "us-east-1")
        model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
        client = boto3.client("bedrock-runtime", region_name=region)

        prompt = f"""Extract term sheet slots from this informal money handshake utterance: "{utterance}"
Return ONLY a valid JSON object with the following fields:
- "direction": "lent" or "borrowed" or null
- "counterparty": string name or pronoun or null
- "amount_inr": float or null
- "deadline_relative": relative string description or null
- "payment_mode": "cash", "upi", "bank", or null
Do not include any extra text or markdown formatting.
"""

        body = json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"temperature": 0.0, "maxTokens": 200}
        })

        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        
        resp_body = json.loads(response["body"].read().decode("utf-8"))
        content_text = resp_body["output"]["message"]["content"][0]["text"].strip()
        
        # Clean JSON markdown backticks if present
        if content_text.startswith("```"):
            content_text = re.sub(r"^```(?:json)?\n?|\n?```$", "", content_text, flags=re.MULTILINE).strip()

        data = json.loads(content_text)

        dir_val = Direction(data.get("direction")) if data.get("direction") in {"lent", "borrowed"} else None
        amt_val = int(float(data["amount_inr"]) * 100) if data.get("amount_inr") is not None else None
        mode_val = PaymentMode(data.get("payment_mode")) if data.get("payment_mode") in {"cash", "upi", "bank"} else None
        
        deadline_val = None
        if data.get("deadline_relative"):
            deadline_val = parse_deadline(data["deadline_relative"], base_dt=base_dt)

        return TermSheet(
            direction=dir_val or parse_direction_and_party(utterance)[0],
            counterparty=data.get("counterparty") or parse_direction_and_party(utterance)[1],
            amount_paise=amt_val or parse_amount_paise(utterance),
            deadline_ts=deadline_val or parse_deadline(utterance, base_dt=base_dt),
            payment_mode=mode_val or parse_payment_mode(utterance)
        )
    except Exception:
        return None

def parse_utterance(utterance: str, base_dt: Optional[datetime] = None) -> TermSheet:
    """Primary parser entry point. Tries Amazon Bedrock first, falling back to deterministic regex."""
    if os.getenv("ENABLE_BEDROCK", "false").lower() in {"true", "1"}:
        parsed = parse_utterance_bedrock(utterance, base_dt=base_dt)
        if parsed is not None:
            return parsed

    return parse_utterance_regex(utterance, base_dt=base_dt)
</file>

<file path="Referee/src/referee/seed.py">
"""
Seed Data Script for Referee Demo.
Populates referee.db with realistic handshake deals for demonstration purposes.
Clearly labeled: DEMO SEED DATA
"""

import os
from datetime import datetime, timedelta, timezone
from referee.store import init_db, create_deal, append_event, get_connection

def seed_database(db_path: str = "referee.db"):
    """Populates database with sample deals in various states (OPEN, OVERDUE, SETTLED)."""
    # Wipe existing tables for a fresh demo reset
    conn = get_connection(db_path)
    with conn:
        conn.execute("DROP TABLE IF EXISTS deal_events")
        conn.execute("DROP TABLE IF EXISTS deals")
    conn.close()

    # Re-initialize DB schema
    init_db(db_path)
    now = datetime.now(timezone.utc)

    print("🌱 Wiped old entries and seeding Referee database with fresh sample demo deals...")

    # --- Deal 1: Rahul (Yellow Card - Overdue by 3 days) ---
    d1_slots = {
        "direction": "lent",
        "counterparty": "Rahul",
        "amount_paise": 200000, # ₹2,000
        "currency": "INR",
        "deadline_ts": (now - timedelta(days=3)).isoformat(),
        "payment_mode": "upi",
        "partial_policy": "accept_partial"
    }
    deal1_id = create_deal("I lent Rahul 2000 rupees, due 3 days ago", d1_slots, db_path=db_path)
    append_event(deal1_id, "locked", {"locked": True}, db_path=db_path)
    append_event(deal1_id, "payment", {"amount_paise": 50000, "mode": "upi"}, db_path=db_path) # ₹500 paid, ₹1500 remaining

    # --- Deal 2: Priya (Red Card - Overdue by 10 days) ---
    d2_slots = {
        "direction": "lent",
        "counterparty": "Priya",
        "amount_paise": 500000, # ₹5,000
        "currency": "INR",
        "deadline_ts": (now - timedelta(days=10)).isoformat(),
        "payment_mode": "bank",
        "partial_policy": "accept_partial"
    }
    deal2_id = create_deal("I lent Priya 5000 for concert tickets", d2_slots, db_path=db_path)
    append_event(deal2_id, "locked", {"locked": True}, db_path=db_path)

    # --- Deal 3: Rohan (Settled Deal - Green Card) ---
    d3_slots = {
        "direction": "lent",
        "counterparty": "Rohan",
        "amount_paise": 100000, # ₹1,000
        "currency": "INR",
        "deadline_ts": (now - timedelta(days=1)).isoformat(),
        "payment_mode": "cash",
        "partial_policy": "accept_partial"
    }
    deal3_id = create_deal("I lent Rohan 1000 cash", d3_slots, db_path=db_path)
    append_event(deal3_id, "locked", {"locked": True}, db_path=db_path)
    append_event(deal3_id, "payment", {"amount_paise": 100000, "mode": "cash"}, db_path=db_path)

    print(f"✅ Seeding complete! Populated 3 sample deals:\n - Rahul (₹1,500 due, Yellow Card)\n - Priya (₹5,000 due, Red Card)\n - Rohan (Fully SETTLED, Green Card)")

if __name__ == "__main__":
    seed_database()
</file>

<file path="Referee/src/referee/verdict.py">
from datetime import datetime, timezone
from typing import Dict, Any, Optional

def compute_verdict(state: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Pure-function verdict engine.
    Calculates balance, payment status, days overdue, and card colour.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    principal_paise = state.get("principal_paise") or state.get("amount_paise") or 0
    paid_paise = state.get("paid_paise") or 0
    balance_paise = max(principal_paise - paid_paise, 0)

    counterparty = state.get("counterparty") or "Counterparty"
    direction = state.get("direction") or "lent"
    partial_policy = state.get("partial_policy") or "accept_partial"

    # Deadline parsing
    deadline_ts_str = state.get("deadline_ts")
    deadline_dt = None
    if deadline_ts_str:
        try:
            deadline_dt = datetime.fromisoformat(deadline_ts_str)
            if deadline_dt.tzinfo is None:
                deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # Status & Colour Logic
    if balance_paise == 0 and principal_paise > 0:
        status = "SETTLED"
        colour = "green"
        days_overdue = 0
    elif deadline_dt and now > deadline_dt and balance_paise > 0:
        status = "OVERDUE"
        time_diff = now - deadline_dt
        days_overdue = max(time_diff.days, 1)

        if 1 <= days_overdue <= 7:
            colour = "yellow"
        else:
            colour = "red"
    else:
        days_overdue = 0
        if paid_paise > 0 and partial_policy != "all_or_nothing":
            status = "PARTIALLY_PAID"
        else:
            status = "OPEN"
        colour = "neutral"

    # Summary formatting
    balance_inr = balance_paise / 100
    if status == "SETTLED":
        one_liner = f"Verdict: Deal with {counterparty} is fully SETTLED. Green card."
    elif status == "OVERDUE":
        verb = "owes you" if direction == "lent" else "you owe"
        card_str = "Yellow card" if colour == "yellow" else "Red card"
        one_liner = f"Verdict: {counterparty} {verb} ₹{balance_inr:.0f}. Deadline passed {days_overdue} day(s) ago. {card_str}."
    else:
        verb = "owes you" if direction == "lent" else "you owe"
        one_liner = f"Verdict: {counterparty} {verb} ₹{balance_inr:.0f}. Status: {status}."

    return {
        "status": status,
        "colour": colour,
        "days_overdue": days_overdue,
        "balance_paise": balance_paise,
        "paid_paise": paid_paise,
        "principal_paise": principal_paise,
        "counterparty": counterparty,
        "one_liner": one_liner
    }
</file>

<file path="Referee/tests/test_extras.py">
import os
import tempfile
import referee.store as store_mod
from referee.store import init_db
from referee.server import propose_deal, answer_question, lock_deal, amend_deal, get_ledger
from referee.links import generate_upi_link, generate_whatsapp_share_link

def test_links_generation():
    upi = generate_upi_link(500.0, payee_vpa="test@upi")
    assert upi is not None
    assert "pa=test%40upi" in upi or "pa=test@upi" in upi
    assert "am=500.00" in upi

    wa = generate_whatsapp_share_link("LENT Rs 500 to Aman")
    assert "https://wa.me/" in wa

def test_amend_and_ledger_flow():
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    
    old_db = store_mod.DEFAULT_DB_PATH
    store_mod.DEFAULT_DB_PATH = db_path
    
    try:
        init_db()
        p_res = propose_deal("I lent Aman 1000")
        deal_id = p_res["deal_id"]
        answer_question(deal_id, "Aman")
        answer_question(deal_id, "UPI")
        lock_deal(deal_id, confirm=True)

        am_res = amend_deal(deal_id, field="amount_inr", new_value="1200")
        assert "deal_id" in am_res, f"amend_deal returned error: {am_res.get('error')}"
        assert am_res["deal_id"] == deal_id

        led_res = get_ledger(counterparty="Aman")
        assert led_res["net_balance_inr"] == 1200.0
    finally:
        store_mod.DEFAULT_DB_PATH = old_db
        if os.path.exists(db_path):
            os.unlink(db_path)
</file>

<file path="Referee/tests/test_parser.py">
from datetime import datetime
from referee.parser import parse_utterance, parse_utterance_regex
from referee.models import Direction

def test_parse_simple_lending():
    utterance = "I lent Aman 1,500, he'll pay Friday"
    base_date = datetime(2026, 10, 21) # Wednesday
    
    sheet = parse_utterance_regex(utterance, base_dt=base_date)
    
    assert sheet.direction == Direction.LENT
    assert sheet.counterparty == "Aman"
    assert sheet.amount_paise == 150000  # Rs 1,500 in paise
    assert sheet.deadline_ts is not None
    assert sheet.deadline_ts.strftime("%Y-%m-%d") == "2026-10-23"  # Friday

def test_parse_utterance_fallback():
    # Verify fallback operates without Bedrock enabled
    sheet = parse_utterance("I borrowed 500 from Rohan")
    assert sheet.direction == Direction.BORROWED
    assert sheet.counterparty == "Rohan"
    assert sheet.amount_paise == 50000
</file>

<file path="Referee/tests/test_simulator.py">
from starlette.testclient import TestClient
from referee.server import app
from referee.store import init_db

def test_simulator_index_route():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Referee — Alexa+ MCP Simulator" in response.text

def test_simulator_tool_api():
    init_db("test_tools.db")
    client = TestClient(app)
    response = client.post("/api/tool/propose_deal", json={"utterance": "I lent Aman 500"})
    assert response.status_code == 200
    data = response.json()
    assert "deal_id" in data
    assert data["slots"]["counterparty"] == "Aman"
</file>

<file path="Referee/tests/test_store.py">
import os
import tempfile
import pytest
from referee.store import init_db, create_deal, append_event, get_deal_state

@pytest.fixture
def test_db():
    db_fd, db_path = tempfile.mkstemp()
    init_db(db_path)
    yield db_path
    os.close(db_fd)
    os.unlink(db_path)

def test_create_and_fold_deal(test_db):
    slots = {
        "direction": "lent",
        "counterparty": "Aman",
        "amount_paise": 100000,
        "payment_mode": "upi"
    }
    deal_id = create_deal("I lent Aman 1000", slots, db_path=test_db)
    
    # Verify initial creation
    state = get_deal_state(deal_id, db_path=test_db)
    assert state is not None
    assert state["counterparty"] == "Aman"
    assert state["balance_paise"] == 100000

    # Lock deal
    append_event(deal_id, "locked", {"locked_by": "user"}, db_path=test_db)
    
    # Log a payment of 400 INR (40000 paise)
    append_event(deal_id, "payment", {"amount_paise": 40000}, db_path=test_db)
    
    # Fold state again and check balance calculation
    updated_state = get_deal_state(deal_id, db_path=test_db)
    assert updated_state is not None
    assert updated_state["paid_paise"] == 40000
    assert updated_state["balance_paise"] == 60000
</file>

<file path="Referee/tests/test_verdict.py">
from datetime import datetime, timedelta, timezone
from referee.verdict import compute_verdict

def test_verdict_settled():
    state = {
        "counterparty": "Aman",
        "direction": "lent",
        "principal_paise": 100000,
        "paid_paise": 100000
    }
    v = compute_verdict(state)
    assert v["status"] == "SETTLED"
    assert v["colour"] == "green"

def test_verdict_yellow_card():
    now = datetime.now(timezone.utc)
    deadline = (now - timedelta(days=3)).isoformat()
    state = {
        "counterparty": "Aman",
        "direction": "lent",
        "principal_paise": 100000,
        "paid_paise": 20000,
        "deadline_ts": deadline
    }
    v = compute_verdict(state, now=now)
    assert v["status"] == "OVERDUE"
    assert v["colour"] == "yellow"
    assert v["days_overdue"] == 3

def test_verdict_red_card():
    now = datetime.now(timezone.utc)
    deadline = (now - timedelta(days=10)).isoformat()
    state = {
        "counterparty": "Aman",
        "direction": "lent",
        "principal_paise": 100000,
        "paid_paise": 0,
        "deadline_ts": deadline
    }
    v = compute_verdict(state, now=now)
    assert v["status"] == "OVERDUE"
    assert v["colour"] == "red"
    assert v["days_overdue"] == 10
</file>

<file path="Referee/.env.example">
# Optional: Your UPI VPA for payment link generation
PAYEE_VPA=yourname@upi
ENABLE_BEDROCK=false
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
</file>

<file path="Referee/.gitignore">
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[codz]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#   Usually these files are written by a python script from a template
#   before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py.cover
*.lcov
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
#   For a library or package, you might want to ignore these files since the code is
#   intended to run in multiple environments; otherwise, check them in:
# .python-version

# pipenv
#   According to pypa/pipenv#598, it is recommended to include Pipfile.lock in version control.
#   However, in case of collaboration, if having platform-specific dependencies or dependencies
#   having no cross-platform support, pipenv may install dependencies that don't work, or not
#   install all needed dependencies.
# Pipfile.lock

# uv
#   Similar to Pipfile.lock, it is generally recommended to include uv.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
# uv.lock

# poetry
#   Similar to Pipfile.lock, it is generally recommended to include poetry.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
#   https://python-poetry.org/docs/basic-usage/#commit-your-poetrylock-file-to-version-control
# poetry.lock
# poetry.toml

# pdm
#   Similar to Pipfile.lock, it is generally recommended to include pdm.lock in version control.
#   pdm recommends including project-wide configuration in pdm.toml, but excluding .pdm-python.
#   https://pdm-project.org/en/latest/usage/project/#working-with-version-control
# pdm.lock
# pdm.toml
.pdm-python
.pdm-build/

# pixi
#   Similar to Pipfile.lock, it is generally recommended to include pixi.lock in version control.
# pixi.lock
#   Pixi creates a virtual environment in the .pixi directory, just like venv module creates one
#   in the .venv directory. It is recommended not to include this directory in version control.
.pixi/*
!.pixi/config.toml

# PEP 582; used by e.g. github.com/David-OConnor/pyflow and github.com/pdm-project/pdm
__pypackages__/

# Celery stuff
celerybeat-schedule*
celerybeat.pid

# Redis
*.rdb
*.aof
*.pid

# RabbitMQ
mnesia/
rabbitmq/
rabbitmq-data/

# ActiveMQ
activemq-data/

# SageMath parsed files
*.sage.py

# Environments
.env
.envrc
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs/Zensical documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
#   JetBrains specific template is maintained in a separate JetBrains.gitignore that can
#   be found at https://github.com/github/gitignore/blob/main/Global/JetBrains.gitignore
#   and can be added to the global gitignore or merged into this file.  For a more nuclear
#   option (not recommended) you can uncomment the following to ignore the entire idea folder.
# .idea/

# Abstra
#   Abstra is an AI-powered process automation framework.
#   Ignore directories containing user credentials, local state, and settings.
#   Learn more at https://abstra.io/docs
.abstra/

# Visual Studio Code
#   Visual Studio Code specific template is maintained in a separate VisualStudioCode.gitignore that
#   can be found at https://github.com/github/gitignore/blob/main/Global/VisualStudioCode.gitignore
#   and can be added to the global gitignore or merged into this file. However, if you prefer, you
#   could uncomment the following to ignore the entire vscode folder
# .vscode/
# Temporary file for partial code execution
tempCodeRunnerFile.py

# Ruff stuff:
.ruff_cache/

# PyPI configuration file
.pypirc

# Marimo
marimo/_static/
marimo/_lsp/
__marimo__/

# Streamlit
.streamlit/secrets.toml

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# pytest
.pytest_cache/

# VS Code / IDE
.vscode/
.idea/
</file>

<file path="Referee/LICENSE">
MIT License

Copyright (c) 2026 Ishaan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
</file>

<file path="Referee/pyproject.toml">
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "referee"
version = "0.1.0"
description = "An MCP server that resolves vague terms in informal agreements."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.0.0",
    "pytest>=8.0.0",
    "python-dateutil>=2.9.0",
    "boto3>=1.34.0"
]

[project.optional-dependencies]
dev = [
    "pytest"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
</file>

<file path="Referee/README.md">
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
</file>

<file path="Referee/Referee_Project_Overview.md">
# Referee — Project Overview & Build Brief

**Entry:** Build, Ship, Shape: Amazon Developer Hackathon (Devpost: amazonappdev2026.devpost.com)
**Primary track:** Alexa+ (self-hosted MCP server, Streamable HTTP, spec 2025-11-25 or later)
**Mini challenges:** AWS Builder and Open Source (each separate $5,000 + $5,000 AWS credits; a project can win only one track prize and one mini-challenge prize)
**Hard deadline:** Fri 23 Oct 2026, 12:00 PM PT = **Sat 24 Oct 2026, 12:30 AM IST**
**Personal submit-by target:** Fri 23 Oct 2026, **6:00 PM IST** (6.5 hours of buffer)
**Builder:** Ishaan (solo). This document is written to be handed to any AI coding assistant.

> Read this whole file before writing code. Sections 1–3 say what to build and why. Section 9 is the working agreement for the AI assistant. Section 8 is the bonus-points plan.

---

## 1. One-line pitch

Alexa reminders remember *when*. **Referee remembers *what you agreed*.**
Say a vague handshake deal out loud; Referee asks the few sharp questions that remove the vagueness, locks the exact terms, tracks payments and amendments across sessions, and later gives a neutral, deterministic verdict.

## 2. The problem (plain English)

Informal deals between friends, family, and freelancers ("I lent Aman 1,500, he'll pay Friday") fail because the terms are vague and shift later: Which Friday? Midnight or evening? Cash or UPI? What if he pays 1,000 first? Nobody records it, so everyone remembers a different version. The problem is tedious, tiny, and mostly ignored, which is why nobody builds for it.

Referee fixes the *vagueness at the moment of the deal*, and keeps an honest record afterwards.

**What it is not:** it does not verify real payments, move money, or create legally enforceable contracts. It is a neutral record of what the user says was agreed and paid. State this plainly in the demo, README, and Devpost text. (Not legal advice.)

## 3. Why this can score well (rubric mapping)

The four judging criteria are equally weighted: Tech Implementation, Design, Potential Impact, Quality of the Idea. Stage 1 is pass/fail: fits the theme and genuinely uses the required tech (a real MCP server).

| Criterion | What Referee shows |
|---|---|
| Tech Implementation | Real MCP server (official Python SDK, Streamable HTTP, spec 2025-11-25+), 7 tools, SQLite state across sessions, deterministic rule engine, Bedrock parsing, test suite, MCP traffic visible in demo |
| Design | Conversational flow with max 3 clarifying questions, defaults offered, read-back before locking, clear verdict card (green / yellow card / red card) |
| Potential Impact | Real, common, India-relevant problem (UPI era, informal lending, shared expenses); credible next steps; works for any currency |
| Quality of the Idea | Rubric explicitly calls "context-aware add-on that maintains state across sessions" creative. Referee's twist: a **rule-based vagueness detector** plus **amendment history** (moving goalposts made visible) |

**Pitch line for judges:** "The model parses; the rules decide."

**Awareness of related public entries (do NOT copy any code or structure):** BorrowBack (equipment loans, simulated, no money terms), Household Constitution (rules for the agent, not between people). No money-handshake entry with a vagueness detector was found on public GitHub as of 21 Oct 2026, but private entries may exist.

---

## 4. Product spec

### 4.1 Core user flow

1. User: "I lent Aman 1,500, he'll pay Friday."
2. Parser (Bedrock, with regex fallback) fills a **term sheet** (4.2).
3. Detector (pure rules, no AI) flags vague slots (4.3). Referee asks **one question at a time, maximum 3**, each with a suggested default. User may say "use defaults".
4. Referee reads the final terms back. User says "lock it". Deal becomes LOCKED. A UPI link and a WhatsApp share link are returned.
5. Later: "Aman paid 500" logs a payment. "Move the deadline to next Monday" logs an amendment. "Did Aman pay?" returns the verdict. "Who owes me what?" returns the ledger.

### 4.2 Term sheet (slots)

| Slot | Meaning | Notes |
|---|---|---|
| `direction` | Who owes whom | "I lent" vs "I borrowed". Never assume; ask if ambiguous |
| `counterparty` | Name of the other person | Must be a real name, not a pronoun |
| `amount_paise` | Integer minor units | Never use floats for money |
| `currency` | Default INR | Ask only if the user hints otherwise |
| `deadline_ts` | Absolute timestamp with timezone | Default timezone Asia/Kolkata |
| `payment_mode` | cash / UPI / bank / other | |
| `partial_policy` | `accept_partial` or `all_or_nothing` | Default `accept_partial`, deadline unchanged |
| `purpose` | Optional free text | Never required |

### 4.3 Vagueness detector rules (the heart of the project)

Deterministic, unit-tested, no network calls. Publish as a standalone package (section 8.2).

| Rule ID | Triggers on | Question asked (with default) |
|---|---|---|
| `DEADLINE_RELATIVE` | weekday names, "next week", "tomorrow", "soon", "later" | "Friday 23 Oct, 11:59 PM IST?" |
| `DEADLINE_FUZZY` | "end of month", "by evening", "in a few days" | Offer a concrete date and time |
| `DEADLINE_CONDITIONAL` | "when he gets paid", "when I need it", "once he can" | "What date should it be due if that hasn't happened?" |
| `AMOUNT_FUZZY` | "around", "about", "~", "some", "a few", ranges | "Exactly how much?" |
| `AMOUNT_UNIT` | "1.5k", "2L", "half" | Echo the normalised number and confirm |
| `PARTY_PRONOUN` | he / she / they / "the guys" / group | "Who exactly? Give me a name." |
| `PARTY_AMBIGUOUS` | two stored counterparties match the same first name | "Aman Sharma or Aman Verma?" |
| `DIRECTION_UNCLEAR` | "gave", "got from", "settled with" | "Does Aman owe you, or do you owe Aman?" |
| `MODE_MISSING` | no cash/UPI/bank mention | "Cash, UPI, or bank transfer?" |
| `PARTIAL_MISSING` | no partial-payment rule stated | "If he pays part, does that count, with the deadline unchanged?" |

Behaviour rules:
- Ask in priority order: direction, counterparty, amount, deadline, mode, partial.
- One question per turn. At most 3 questions per deal; after that apply defaults and say which defaults were applied.
- Every question includes a proposed default so a one-word answer finishes it.
- Never lock a deal while a `DIRECTION_UNCLEAR`, `PARTY_PRONOUN`, or `AMOUNT_FUZZY` flag is open.

### 4.4 MCP tools (7)

Core 5 first. Items 6–7 are the approved extras; build them only after the core works end to end.

| # | Tool | Input | Output (structured) |
|---|---|---|---|
| 1 | `propose_deal` | `utterance: str` | `deal_id`, parsed slots, `open_flags[]`, `next_question` (or null), `defaults_applied[]` |
| 2 | `answer_question` | `deal_id`, `answer: str` | updated slots, remaining flags, next question or `ready_to_lock: true`, read-back text |
| 3 | `lock_deal` | `deal_id`, `confirm: true` | locked terms, `upi_link`, `whatsapp_share_link`, `locked_at`. Refuses if flags remain or `confirm` is not true |
| 4 | `log_payment` | `deal_id` or `counterparty`, `amount`, optional `mode`, optional `when` | updated balance, status, event id |
| 5 | `get_verdict` | `deal_id` or `counterparty` | verdict card payload (4.6) |
| 6 | `amend_deal` | `deal_id`, `field`, `new_value`, `reason?` | amendment event, original vs current terms, full amendment history. Never overwrites the original |
| 7 | `get_ledger` | optional `counterparty` | per-person net balances across all deals, each with status |

All tools return `structuredContent` plus a short, speakable `summary` string suitable for text-to-speech.

### 4.5 Data model (SQLite, append-only events)

```
deals(id, direction, counterparty, currency, mode, partial_policy,
      principal_paise, deadline_ts, status, purpose, raw_utterance,
      created_at, locked_at)

deal_events(id, deal_id, type, payload_json, ts)
  type ∈ created | term_set | locked | payment | amended
```

- Terms at lock time are frozen in the `locked` event. `amend_deal` appends an `amended` event; the original is never edited.
- Balance and status are **derived** by folding events, not stored separately.
- Optional stretch (about 20 lines): store `sha256(prev_hash + payload)` on each event for a tamper-evident chain. Skip if time is tight; do not over-claim it.

### 4.6 Verdict logic (deterministic, unit-tested)

Inputs: current terms (original plus amendments), payments, now.

- `paid_paise = sum(payments)`, `balance_paise = principal - paid`
- Status: `OPEN`, `PARTIALLY_PAID`, `SETTLED`, `OVERDUE` (derived when now > deadline and balance > 0)
- `days_overdue` = whole days past the current deadline
- Card colour (thresholds are tunable constants):
  - green: SETTLED
  - neutral: OPEN or PARTIALLY_PAID before deadline
  - **yellow card:** overdue 1–7 days
  - **red card:** overdue more than 7 days
- If `partial_policy = all_or_nothing`, a partial payment is recorded but does not change status.
- Verdict payload: status, colour, balance, days overdue, original terms, amendment history, payment list, plain-English one-liner. Example one-liner: "Verdict: Aman owes ₹500. Deadline passed 2 days ago. Yellow card."

### 4.7 Links

- **UPI link** (real standard): `upi://pay?pa=<payee_vpa>&pn=<name>&am=<amount>&cu=INR&tn=<note>`. The payee VPA is the lender's own, supplied once via a config/env value or a `set_profile` helper. If absent, omit the link rather than fabricate one.
- **WhatsApp share:** `https://wa.me/?text=<urlencoded terms text>` so the counterparty can reply "agreed". This reduces the one-sided-lock weakness.

---

## 5. Architecture and tech stack (mostly free)

```
Browser simulator (chat + mic)  ──►  Simulator host (intent → tool calls)
                                              │  MCP client
                                              ▼
Alexa+ (real, optional) ───────►  Referee MCP server  /mcp  (Streamable HTTP)
                                   ├─ detector (pure Python)
                                   ├─ SQLite (events)
                                   ├─ verdict engine
                                   └─ Bedrock parser (fallback: regex)
```

| Layer | Choice | Cost |
|---|---|---|
| Language | Python 3.11+ | Free |
| MCP server | Official `mcp` Python SDK (`pip install "mcp[cli]"`), FastMCP, `transport="streamable-http"`, endpoint `/mcp` | Free |
| State | SQLite (stdlib `sqlite3`) | Free |
| Tests | `pytest` | Free |
| Parser | Amazon Bedrock (an Amazon Nova model; check the console for the model ID available in your region) **with a deterministic regex/dateparser fallback** so the project works at zero cost | Pennies; hackathon AWS credit codes are exhausted, so check whether your AWS account has free-tier credit |
| Simulator UI | Single HTML + vanilla JS; browser Web Speech API for the mic (Chrome) | Free |
| HTTPS for testing | Cloudflare Tunnel (`cloudflared`) or similar free tunnel | Free |
| Optional hosting | A free tier (for example Render; free instances may cold-start) | Free |
| Repo, video | GitHub (public), YouTube (public), OBS Studio for screen recording | Free |
| MCP debugging | MCP Inspector (`npx @modelcontextprotocol/inspector`) | Free |

Notes for the AI assistant:
- Confirm via MCP Inspector that `initialize` negotiates protocol **2025-11-25 or later**. If the installed SDK negotiates an older version, upgrade it.
- The legacy SSE transport is not accepted by Alexa+. Use Streamable HTTP only.
- The simulator host may be rule-based or Bedrock-based. Show the MCP JSON-RPC traffic in a side panel; it proves the server is really called.
- Mount simulator routes next to `/mcp` (FastMCP custom routes or a small Starlette parent app).
- Add an `Origin` check and an optional bearer token on `/mcp` if the server is public.
- Alexa+ account linking is **optional**; do not build OAuth. Real Alexa+ onboarding uses the `alexa-ai` CLI and needs an Alexa developer account and Alexa+ preview access, which may not be available. The rules allow a **simulated Alexa+ experience** instead, provided the repo contains the simulator's source and the video clearly shows it working.

---

## 6. Hackathon rules checklist (from the official rules; re-verify on the Devpost Rules page before submitting)

**Eligibility:** age of majority in country of residence; India is allowed. Solo is fine.

**Project requirements**
- [ ] Project is new or significantly updated during the window (31 Aug – 23 Oct 2026). Referee is new: first commit must be dated inside the window, and the Devpost text must say so.
- [ ] Alexa+ track: working self-hosted MCP server (spec 2025-11-25+, Streamable HTTP) **or** a simulated Alexa+ experience with its source in the repo.
- [ ] Repo **actually calls** the MCP technology at runtime (import and entry point in code), not only mentioned in the README.
- [ ] Repo has clear setup and run instructions.
- [ ] Original work, solely owned by the entrant; third-party SDKs and data used per their licenses.
- [ ] Nothing in the project is derived from Amazon/Devpost-funded or contracted work.

**Repository access (pick one)**
- Public repo **with a visible open-source license file** (License shown in the About section), **or**
- Private repo shared with Devpost's required email (see the "What to Submit" section on the Devpost page) **and** these GitHub users: `knmeiss`, `giolaq`, `anishamalde`, `mosesroth`, `emersonsklar`.
- Invites expire after 7 days and each person must accept. Add them **on submit day**.
- Recommended: public repo with MIT license (also needed for the Open Source mini challenge).

**Submission items (Devpost form)**
- [ ] Text description (features and how it works)
- [ ] GitHub repo URL
- [ ] Demo video **under 3 minutes**, public on YouTube or Vimeo, in English, showing the project working on the intended platform; judges are not required to watch beyond 3:00
- [ ] No third-party trademarks or copyrighted music/footage in the video
- [ ] Product feedback for **every** tool, API, or SDK used (mandatory)
- [ ] Track selected: Alexa+; mini challenges selected: AWS Builder, Open Source
- [ ] If any part existed before the window: explanation of what changed (not expected here)
- [ ] Optional: feature requests, friction log entries

**Other rules**
- Submissions cannot be edited after the deadline.
- Judges may judge from the text and video alone, so the video carries the project.
- Winners are verified (identity and role in creating the submission) and must complete tax forms; prizes are paid after affidavit.
- Fabricating content, tampering with the process, or violating the rules can lead to disqualification.

---

## 7. Build plan (target: submitted by 6 PM IST on 23 Oct)

| Phase | Window (IST) | Goal | Done when |
|---|---|---|---|
| 0 Setup | Thu 22 Oct, first 1–2 h | Join Devpost hackathon; create public GitHub repo with MIT license and README stub (first commit in window); install Python deps, Inspector; request Bedrock model access; start `FRICTION_NOTES.md` | Repo public; hello-world MCP tool visible in Inspector |
| 1 Core | Thu 22 Oct, to ~2 PM | Detector + unit tests; SQLite events; tools 1–3 | `propose_deal` → `answer_question` → `lock_deal` works end to end in Inspector; detector tests green |
| 2 Rest | Thu 22 Oct, 2 PM – ~10 PM | Tools 4–5 (payments, verdict); then 6–7 (amend, ledger); UPI and WhatsApp links; simulator page with verdict card | Full demo story runs start to finish |
| 3 Polish | Fri 23 Oct, 8 AM – 12 PM | Tunnel or deploy; card styling; README; tests green; error handling | **Feature freeze at 12 PM IST on 23 Oct** |
| 4 Ship | Fri 23 Oct, 12 PM – 6 PM | Record video; write friction log and product feedback; Devpost form; add reviewers if private; **submit** | Submission confirmation received |
| Buffer | 6 PM IST → deadline (12:30 AM IST Sat) | Fix only broken links or access problems | — |

**Cut line:** if the core (tools 1–5 plus detector) is not working by Thursday night, drop tools 6–7 and the fancy card. A polished 5-tool demo beats a shaky 7-tool one.

**Explicitly out of scope:** user accounts, counterparty app, notifications, group splits, payment verification, OCR, anything on-chain.

---

## 8. Bonus points and extra prizes — everything to do

### 8.1 Friction log (up to **10% judging bonus**)

How it is scored: Amazon's internal review team assesses friction-log entries at the Stage 1 down-select and passes a recommended bonus (up to 10%) to the Stage 2 panel, which adds it to the final score. Entries are therefore judged on being **specific, reproducible, and actionable**.

**Integrity rule (important):** entries must describe things that **actually happened** to the builder. Never invent or pad friction entries. The aim is genuine developer-experience feedback; fabricated logs could hurt credibility and risk disqualification. Fewer true, detailed entries beat many vague ones. Aim for roughly 6–10 real entries.

**Entry template** (all fields requested by the rules):

```
## FL-<n>: <short title>
- Tool / API / SDK: <e.g. mcp Python SDK vX, Bedrock, MCP Inspector, alexa-ai CLI, Alexa+ simulator, Devpost docs>
- Task attempted: <what you were trying to do>
- Steps taken: <numbered, reproducible>
- Expected: <what you thought would happen>
- Actual: <what happened, include exact error text or a screenshot filename>
- Severity: <Blocker | Major | Minor | Cosmetic>
- Workaround used: <what you did, or "none">
- Suggestion: <specific, actionable change for the owning team>
```

**Workflow for a builder with no time to write these:**
1. During the build, append one raw line to `FRICTION_NOTES.md` the moment something annoys you: timestamp, tool, 5–10 words. Example: `Thu 3:40pm | Inspector | session id lost after restart, no clear error`.
2. Save exact error messages and screenshots in `docs/friction/`.
3. At the end, give the raw notes to an AI (Claude works well) to expand into the template above. The AI must ask for missing details (expected vs actual, steps) and must **not** invent anything not in the notes.
4. Save as `docs/FRICTION_LOG.md` in the repo **and** paste into the Devpost friction field.

**Places friction is likely to occur (watch for these; log only what really happens):**
- SDK protocol-version negotiation vs the required 2025-11-25
- Streamable HTTP session handling and Inspector behaviour
- Tunnel/HTTPS setup for remote testing
- `alexa-ai` CLI install, login, or add-on scaffolding (if attempted)
- Alexa+ preview or simulator access
- Bedrock model access approval, region, quota, or latency
- Devpost form fields or repo-sharing steps
- Gaps in the Alexa+ MCP docs (for example, tool-result rendering or card support)

### 8.2 Open Source mini challenge ($5,000 + $5,000 AWS credits)

Requirement: a **new, additional** open-source project, or a contribution (branch, fork, or PR; need not be merged) to a public repo, made **during the window**, alongside the primary submission.

Plan: publish the vagueness detector as its own repo, **`vagueterms`**:
- Separate public GitHub repo, MIT license visible, created inside the window
- Pure Python, no network dependency, README with examples, a real test suite, installable with `pip install -e .`
- Referee imports it (so it is genuinely used, not decorative)
- Rule table from section 4.3 documented as the public API

Do not use "added a license file to the main repo" as the contribution; the rules call trivial changes "obvious".

Required fields on Devpost for this challenge: contribution URL, repo URL, GitHub username, and a short description of what you did, how it works, and why it matters.

Optional extra (if time remains): a small genuine PR (docs fix or bug fix) to a public MCP-related repo, linked as a second contribution. Only if it is real.

### 8.3 AWS Builder mini challenge ($5,000 + $5,000 AWS credits)

Requirement: use AWS services with **documented integrations**. Qualifies: Bedrock, AgentCore, Strands SDK, SageMaker, Kiro Crew.
- Use Bedrock for utterance → term-sheet parsing, with structured JSON output.
- In the Product Feedback answer, describe which AWS services were used and how (the rules require this there).
- Keep the regex fallback so the demo never depends on AWS being up.
- Judges' "obvious" example for this challenge is a single Bedrock text-generation call. Make the integration meaningful: a constrained parse step feeding a deterministic rule engine, with the model never deciding the verdict.

### 8.4 Other ways to score

- **Product feedback:** mandatory; make it thorough and honest (tools used, what worked, what needs work, onboarding experience, would you build again and why).
- **Optional feature requests:** description, why it matters, priority (Critical / Important / Nice-to-have). Cheap and appreciated.
- **First 30 seconds of the video** show the finished verdict card, then rewind to the story.
- **Visible tests and clean git history** (commits dated inside the window) support "built during the hackathon".
- **Be honest about what is simulated** (Alexa+ host, UPI payment verification). Overclaiming is penalised in credibility; judges reward clarity.
- **MCP Apps** are listed as a creative Alexa+ feature. Only claim it if the verdict card is genuinely delivered as an MCP App resource; otherwise call it a "card rendered in the simulator".

---

## 9. Working agreement for the AI assistant

1. **Follow the spec; ask before changing scope.** Do not add features outside sections 4 and 7.
2. **Build in order:** detector + tests → tools 1–3 → tools 4–5 → extras. Each step must run and be demonstrable in MCP Inspector before moving on.
3. **Determinism first:** the detector and verdict logic must be pure functions with unit tests. The model never decides a verdict.
4. **Money is integers** (paise). Timezone-aware datetimes (default Asia/Kolkata). Test the date parsing around "Friday" edge cases (today is Friday, week boundaries).
5. **No fake data presented as real.** Seed demo data may exist but must be labelled as seed data.
6. **Don't copy other hackathon entries.** Original work only.
7. **Keep secrets out of git** (AWS keys, tokens). Use environment variables and `.env.example`.
8. **Log friction honestly:** whenever the builder hits a tool or docs problem, append a raw line to `FRICTION_NOTES.md` and keep the exact error text.
9. **Keep the README current:** setup, run, test, tools table, what is real vs simulated, license.
10. **Report blockers early** with the exact error and the proposed cut.

### Definition of done

- [ ] `pytest` green (detector, verdict, tools)
- [ ] MCP Inspector shows 7 tools; `initialize` negotiates ≥ 2025-11-25
- [ ] Demo story runs end to end in the simulator
- [ ] Public repo with visible MIT license, run instructions, first commit inside the window
- [ ] `vagueterms` repo public, tested, imported by Referee
- [ ] Video under 3:00, public, English, no copyrighted music
- [ ] Friction log, product feedback, and Devpost form complete
- [ ] Reviewers added (if repo is private) and submission confirmed before 6 PM IST on 23 Oct

---

## 10. Demo video script (target 2:40, hard cap 3:00)

| Time | Scene |
|---|---|
| 0:00–0:20 | Hook: show the finished **yellow-card verdict** with the one-liner, then: "Reminders remember when. Referee remembers what you agreed." |
| 0:20–1:10 | Voice: "I lent Aman 1,500, he'll pay Friday." Referee asks 2–3 sharp questions with defaults; read-back; "lock it"; UPI and WhatsApp links appear |
| 1:10–1:40 | "Aman paid 500." Balance updates. "Move the deadline to Monday." Amendment history shows original vs new |
| 1:40–2:10 | Next day (new session): "Did Aman pay?" → verdict card. "Who owes me what?" → ledger |
| 2:10–2:30 | Brief look at MCP JSON-RPC traffic and test suite; say what is simulated and what is real |
| 2:30–2:40 | Close: real MCP server, rule-based detector published as open source, built with Bedrock |

Record with OBS. Use your own voice or original audio only. Upload as public on YouTube.

---

## 11. Repository layout (suggested)

```
referee/
├─ README.md            # what/why, run, test, tools, real vs simulated, license
├─ LICENSE              # MIT, visible in repo root
├─ .env.example
├─ pyproject.toml
├─ src/referee/
│  ├─ server.py         # FastMCP app, 7 tools, /mcp
│  ├─ parser.py         # Bedrock parse + regex fallback
│  ├─ verdict.py        # deterministic engine
│  ├─ store.py          # SQLite events
│  ├─ links.py          # UPI + wa.me builders
│  └─ simulator/        # host + static UI (index.html, app.js)
├─ tests/
├─ docs/
│  ├─ FRICTION_LOG.md
│  ├─ PRODUCT_FEEDBACK.md
│  ├─ friction/         # screenshots and raw errors
│  └─ ARCHITECTURE.md
└─ FRICTION_NOTES.md    # raw notes during the build
# separate public repo: vagueterms/  (MIT, detector package + tests)
```

---

## 12. Known risks and honest weaknesses

- **Crowded track.** Many public Alexa+ entries exist; execution quality, a real working MCP server, and the video decide this.
- **One-sided record.** Referee cannot prove the other person agreed or that money moved. Mitigation: share link, honest framing.
- **Time.** About 36 working hours. The cut line in section 7 is binding.
- **Alexa+ access.** Real device or preview access may be unavailable; the simulated path is explicitly allowed.
- **Bedrock access or cost.** Mitigated by the regex fallback.
- **Builder has another event right after the deadline.** Submit early; do not use the last night as working time.

---

## 13. Quick reference

- Devpost page: amazonappdev2026.devpost.com (Rules, Resources, FAQs, Updates tabs)
- Alexa+ MCP Toolkit quickstart: developer.amazon.com/docs/alexaplus/add-ons/mcp-toolkit-quickstart
- Reviewer GitHub usernames (private-repo option): knmeiss, giolaq, anishamalde, mosesroth, emersonsklar
- Prizes in play for this entry: Alexa+ track (1st $25,000 / 2nd $15,000 / 3rd $4,000) plus one mini challenge ($5,000 each)
- Judging: Stage 1 pass/fail on theme fit and real use of required tech; Stage 2 four equal criteria; friction log bonus up to 10%
- Judging period 9–20 Nov 2026; winners around 3 Dec 2026
</file>

<file path="vagueterms/src/vagueterms.egg-info/dependency_links.txt">

</file>

<file path="vagueterms/src/vagueterms.egg-info/PKG-INFO">
Metadata-Version: 2.4
Name: vagueterms
Version: 0.1.0
Summary: A deterministic rules engine to detect vague terms in money handshakes.
Requires-Python: >=3.11
Description-Content-Type: text/markdown
License-File: LICENSE
Requires-Dist: python-dateutil>=2.9.0
Provides-Extra: dev
Requires-Dist: pytest>=8.0.0; extra == "dev"
Dynamic: license-file

# vagueterms

A deterministic, pure-Python rules engine that detects vague terms (dates, amounts, parties) in informal financial agreements. 
Built for the Referee project (Amazon Developer Hackathon 2026).
</file>

<file path="vagueterms/src/vagueterms.egg-info/requires.txt">
python-dateutil>=2.9.0

[dev]
pytest>=8.0.0
</file>

<file path="vagueterms/src/vagueterms.egg-info/SOURCES.txt">
LICENSE
README.md
pyproject.toml
src/vagueterms/__init__.py
src/vagueterms.egg-info/PKG-INFO
src/vagueterms.egg-info/SOURCES.txt
src/vagueterms.egg-info/dependency_links.txt
src/vagueterms.egg-info/requires.txt
src/vagueterms.egg-info/top_level.txt
</file>

<file path="vagueterms/src/vagueterms.egg-info/top_level.txt">
vagueterms
</file>

<file path="vagueterms/tests/__init__.py">

</file>

<file path="vagueterms/tests/test_detector.py">
from vagueterms.detector import detect_vague_terms, DIRECTION_UNCLEAR, PARTY_PRONOUN, AMOUNT_FUZZY

def test_direction_and_pronoun_flagged():
    slots = {"counterparty": "he", "amount_paise": 150000}
    flags, next_q, _ = detect_vague_terms(slots, "he owes me 1500 around Friday")
    
    assert DIRECTION_UNCLEAR in flags
    assert PARTY_PRONOUN in flags
    assert next_q is not None
    assert next_q.rule_id == DIRECTION_UNCLEAR  # Highest priority

def test_blocking_flags():
    slots = {"direction": "lent", "counterparty": "Aman", "amount_paise": None}
    flags, next_q, _ = detect_vague_terms(slots, "I lent Aman about 1500")
    
    assert AMOUNT_FUZZY in flags
    assert next_q is not None
    assert next_q.rule_id == AMOUNT_FUZZY
</file>

<file path="vagueterms/.gitignore">

</file>

<file path="vagueterms/LICENSE">
MIT License

Copyright (c) 2026 Ishaan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
</file>

<file path="vagueterms/pyproject.toml">
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "vagueterms"
version = "0.1.0"
description = "A deterministic rules engine to detect vague terms in money handshakes."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "python-dateutil>=2.9.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
</file>

<file path="vagueterms/README.md">
# vagueterms

A deterministic, pure-Python rules engine that detects vague terms (dates, amounts, parties) in informal financial agreements. 
Built for the Referee project (Amazon Developer Hackathon 2026).
</file>

<file path="Referee/src/referee/store.py">
import sqlite3
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

DEFAULT_DB_PATH = "referee.db"

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the SQLite database with deals and deal_events tables."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id TEXT PRIMARY KEY,
                direction TEXT,
                counterparty TEXT,
                currency TEXT DEFAULT 'INR',
                mode TEXT,
                partial_policy TEXT DEFAULT 'accept_partial',
                principal_paise INTEGER,
                deadline_ts TEXT,
                status TEXT DEFAULT 'PROPOSED',
                purpose TEXT,
                raw_utterance TEXT,
                created_at TEXT,
                locked_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deal_events (
                id TEXT PRIMARY KEY,
                deal_id TEXT NOT NULL,
                type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                ts TEXT NOT NULL,
                FOREIGN KEY(deal_id) REFERENCES deals(id)
            )
        """)
    conn.close()

def create_deal(
    raw_utterance: str,
    slots: Dict[str, Any],
    db_path: Optional[str] = None
) -> str:
    """Creates a new deal record and appends a 'created' event."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    deal_id = str(uuid.uuid4())[:8]
    now_iso = datetime.now(timezone.utc).isoformat()
    
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            INSERT INTO deals (id, direction, counterparty, currency, mode, partial_policy, principal_paise, deadline_ts, status, purpose, raw_utterance, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PROPOSED', ?, ?, ?)
        """, (
            deal_id,
            slots.get("direction"),
            slots.get("counterparty"),
            slots.get("currency", "INR"),
            slots.get("payment_mode"),
            slots.get("partial_policy", "accept_partial"),
            slots.get("amount_paise"),
            slots.get("deadline_ts"),
            slots.get("purpose"),
            raw_utterance,
            now_iso
        ))
        
        event_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO deal_events (id, deal_id, type, payload_json, ts)
            VALUES (?, ?, 'created', ?, ?)
        """, (event_id, deal_id, json.dumps(slots), now_iso))
        
    conn.close()
    return deal_id

def append_event(
    deal_id: str,
    event_type: str,
    payload: Dict[str, Any],
    db_path: Optional[str] = None
) -> str:
    """Appends an event to the append-only event log."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    event_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            INSERT INTO deal_events (id, deal_id, type, payload_json, ts)
            VALUES (?, ?, ?, ?, ?)
        """, (event_id, deal_id, event_type, json.dumps(payload), now_iso))
        
        if event_type == "locked":
            conn.execute("UPDATE deals SET status = 'LOCKED', locked_at = ? WHERE id = ?", (now_iso, deal_id))
            
    conn.close()
    return event_id

def get_deal_events(deal_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches all events for a deal ordered by timestamp."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, payload_json, ts FROM deal_events WHERE deal_id = ? ORDER BY ts ASC", (deal_id,))
    rows = cursor.fetchall()
    conn.close()
    
    events = []
    for row in rows:
        events.append({
            "id": row["id"],
            "type": row["type"],
            "payload": json.loads(row["payload_json"]),
            "ts": row["ts"]
        })
    return events

def get_deal_state(deal_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Derives current deal state by folding its event history."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deals WHERE id = ?", (deal_id,))
    deal_row = cursor.fetchone()
    conn.close()

    if not deal_row:
        return None

    state = dict(deal_row)
    events = get_deal_events(deal_id, db_path)
    
    # Map DB column names to detector slot names
    state["amount_paise"] = state.get("principal_paise")
    state["payment_mode"] = state.get("mode")

    paid_paise = 0
    payments = []
    amendments = []

    for ev in events:
        ev_type = ev["type"]
        payload = ev["payload"]
        
        if ev_type == "term_set":
            for k, v in payload.items():
                state[k] = v
                if k == "payment_mode":
                    state["mode"] = v
                if k == "amount_paise":
                    state["principal_paise"] = v
        elif ev_type == "payment":
            amount = payload.get("amount_paise", 0)
            paid_paise += amount
            payments.append(payload)
        elif ev_type == "amended":
            amendments.append(payload)
            field = payload.get("field")
            if field:
                new_val = payload.get("new_value")
                state[field] = new_val
                if field == "principal_paise":
                    state["amount_paise"] = new_val
                elif field == "payment_mode":
                    state["mode"] = new_val

    principal = state.get("principal_paise") or 0
    balance = principal - paid_paise

    state["paid_paise"] = paid_paise
    state["balance_paise"] = max(balance, 0)
    state["payments"] = payments
    state["amendments"] = amendments
    
    return state
</file>

<file path="Referee/tests/test_server.py">
from referee.server import ping, mcp

def test_ping():
    """Verify that the ping tool returns 'pong'."""
    assert ping() == "pong"

def test_server_name():
    """Verify MCP server instance name."""
    assert mcp.name == "Referee"
</file>

<file path="Referee/tests/test_tools.py">
import os
import referee.store as store_mod
from referee.store import init_db
from referee.server import propose_deal, answer_question, lock_deal, log_payment, get_verdict

def setup_module(module):
    store_mod.DEFAULT_DB_PATH = "test_tools.db"
    init_db("test_tools.db")

def test_full_deal_flow():
    p_res = propose_deal("I lent Aman 1500, he'll pay Friday")
    deal_id = p_res["deal_id"]
    assert deal_id is not None
    assert p_res["open_flags"]
    
    a_res = answer_question(deal_id, "UPI")
    assert a_res["ready_to_lock"] is True
    
    l_res = lock_deal(deal_id, confirm=True)
    assert l_res["status"] == "LOCKED"

def test_log_payment_and_verdict_flow():
    p_res = propose_deal("I lent Aman 1000 rupees")
    deal_id = p_res["deal_id"]
    
    answer_question(deal_id, "Aman")
    answer_question(deal_id, "UPI")
    lock_deal(deal_id, confirm=True)

    pay_res = log_payment(amount_inr=400.0, deal_id=deal_id)
    assert pay_res["updated_balance_inr"] == 600.0

    v_res = get_verdict(deal_id=deal_id)
    assert v_res["verdict_card"]["balance_paise"] == 60000
</file>

<file path="Referee/FRICTION_NOTES.md">
# FRICTION_NOTES.md

Wed 6:48pm | Setup | Started project skeleton
Wed 7:00pm | mcp SDK | FastMCP renamed to MCPServer in mcp v2.x breaking v1 code imports
Wed 7:05pm | MCP Inspector | Manual toggle required to connect server before negotiating protocol 2025-11-25
Wed 7:25pm | Virtualenv | Moving project folder broke pip launcher hardcoded absolute paths, required recreation
Wed 8:00pm | Pylance | Strict type checking flagged Optional return values in tests requiring explicit is not None assertions
Wed 8:50pm | Store/Detector | Schema column name mismatch (principal_paise/mode vs amount_paise/payment_mode) broke ready_to_lock status
Wed 10:15pm | Simulator UI | Flexbox container overflow pushed chat input box off-screen after two message exchanges
Wed 10:20pm | Simulator Host | Deal context lost after lock, causing log_payment and get_verdict to fail without active deal_id
Wed 10:22pm | vagueterms / Server | Affirmative "yes" responses failed to register, trapping user in infinite clarifying question loop
Wed 10:30pm | MCP Inspector | Default filesystem server failed on Windows due to unmapped /tmp directory
Wed 10:35pm | Starlette / MCP SDK | Mount("/mcp") issued automatic 307 redirect to /mcp/, breaking Inspector POST requests with 404
Wed 10:38pm | Pylance / MCP SDK | FastMCP class import raised attribute error due to SDK rename to MCPServer in mcp.server.mcpserver
Wed 10:42pm | Starlette / MCP SDK | POST /mcp failed with 500 Internal Server Error (RuntimeError: Task group is not initialized) due to unhandled Starlette lifespan context
Wed 11:05pm | Pylance / Bedrock | Import "boto3" missing from pyproject.toml dependencies causing reportMissingImports
Wed 11:25pm | Simulator UI | String matching in app.js missed named queries ("Did Aman pay?"), routing queries to propose_deal and trapping users in a clarification loop
Wed 11:35pm | Simulator UI | Intent classification order prioritized active deal state over general queries and cancellation commands, trapping user in rigid Q&A procedures
Wed 11:50pm | Server / Verdict | Single-deal payment logging caused total balance confusion when multiple deals existed for the same counterparty; resolved via FIFO waterfall logic
Wed 11:58pm | Simulator / Server | Duplicate counterparties caused merged ledgers without confirmation; resolved with PARTY_AMBIGUOUS disambiguation and conversational chitchat interceptors
</file>

<file path="vagueterms/src/vagueterms/__init__.py">
from .detector import detect_vague_terms, BLOCKING_FLAGS, PRIORITY_ORDER

__all__ = ["detect_vague_terms", "BLOCKING_FLAGS", "PRIORITY_ORDER"]
</file>

<file path="vagueterms/src/vagueterms/detector.py">
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

# Rule ID constants
DEADLINE_RELATIVE = "DEADLINE_RELATIVE"
DEADLINE_FUZZY = "DEADLINE_FUZZY"
DEADLINE_CONDITIONAL = "DEADLINE_CONDITIONAL"
AMOUNT_FUZZY = "AMOUNT_FUZZY"
AMOUNT_UNIT = "AMOUNT_UNIT"
PARTY_PRONOUN = "PARTY_PRONOUN"
PARTY_AMBIGUOUS = "PARTY_AMBIGUOUS"
DIRECTION_UNCLEAR = "DIRECTION_UNCLEAR"
MODE_MISSING = "MODE_MISSING"
PARTIAL_MISSING = "PARTIAL_MISSING"

# Blocking flags that prevent locking a deal
BLOCKING_FLAGS = {DIRECTION_UNCLEAR, PARTY_PRONOUN, PARTY_AMBIGUOUS, AMOUNT_FUZZY}

# Priority order for asking clarifying questions
PRIORITY_ORDER = [
    DIRECTION_UNCLEAR,
    PARTY_PRONOUN,
    PARTY_AMBIGUOUS,
    AMOUNT_FUZZY,
    AMOUNT_UNIT,
    DEADLINE_RELATIVE,
    DEADLINE_FUZZY,
    DEADLINE_CONDITIONAL,
    MODE_MISSING,
    PARTIAL_MISSING,
]

PRONOUNS = {"he", "she", "they", "them", "him", "her", "guys", "group", "someone", "friend"}

@dataclass
class Question:
    rule_id: str
    prompt: str
    proposed_default: Any

def detect_vague_terms(
    slots: Dict[str, Any],
    raw_utterance: str,
    matching_counterparties: Optional[List[str]] = None
) -> Tuple[List[str], Optional[Question], List[str]]:
    """Pure-function detector for vague handshake terms."""
    flags = []
    utterance_lower = raw_utterance.lower()

    # Rule 1: DIRECTION_UNCLEAR
    if not slots.get("direction"):
        flags.append(DIRECTION_UNCLEAR)

    # Rule 2: PARTY_PRONOUN
    counterparty = slots.get("counterparty")
    if not counterparty or counterparty.lower() in PRONOUNS:
        flags.append(PARTY_PRONOUN)

    # Rule 3: PARTY_AMBIGUOUS (Triggers if existing matching counterparties exist in DB and haven't been confirmed)
    if counterparty and counterparty.lower() not in PRONOUNS and matching_counterparties and not slots.get("party_confirmed"):
        flags.append(PARTY_AMBIGUOUS)

    # Rule 4: AMOUNT_FUZZY
    if re.search(r"\b(around|about|approx|approximately|~|some|a few)\b", utterance_lower) or not slots.get("amount_paise"):
        flags.append(AMOUNT_FUZZY)

    # Rule 5: AMOUNT_UNIT
    if not slots.get("amount_confirmed") and re.search(r"\b(\d+k|\d+l|half)\b", utterance_lower):
        flags.append(AMOUNT_UNIT)

    # Rule 6: DEADLINE_RELATIVE
    if not slots.get("deadline_confirmed") and re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|next week|tomorrow|later)\b", utterance_lower):
        flags.append(DEADLINE_RELATIVE)

    # Rule 7: DEADLINE_FUZZY
    if not slots.get("deadline_confirmed") and re.search(r"\b(end of month|by evening|in a few days|soon)\b", utterance_lower):
        flags.append(DEADLINE_FUZZY)

    # Rule 8: DEADLINE_CONDITIONAL
    if not slots.get("deadline_confirmed") and re.search(r"\b(when he gets paid|when i need it|once he can|whenever)\b", utterance_lower):
        flags.append(DEADLINE_CONDITIONAL)

    # Rule 9: MODE_MISSING
    if not slots.get("payment_mode"):
        flags.append(MODE_MISSING)

    # Rule 10: PARTIAL_MISSING
    if not slots.get("partial_policy"):
        flags.append(PARTIAL_MISSING)

    party_name = counterparty.capitalize() if counterparty else "that person"
    
    # Questions mapping
    questions_map = {
        DIRECTION_UNCLEAR: Question(DIRECTION_UNCLEAR, "Does the other person owe you, or do you owe them?", "lent"),
        PARTY_PRONOUN: Question(PARTY_PRONOUN, "Who exactly? Give me a full name.", None),
        PARTY_AMBIGUOUS: Question(PARTY_AMBIGUOUS, f"You already have active deals with {party_name}. Is this the same {party_name}, or a different person?", "same"),
        AMOUNT_FUZZY: Question(AMOUNT_FUZZY, "Exactly how much was agreed in total?", None),
        AMOUNT_UNIT: Question(AMOUNT_UNIT, "Can you confirm the exact total amount in Rupees?", slots.get("amount_paise")),
        DEADLINE_RELATIVE: Question(DEADLINE_RELATIVE, "Is Friday 11:59 PM IST acceptable as the exact deadline?", "Friday 11:59 PM IST"),
        DEADLINE_FUZZY: Question(DEADLINE_FUZZY, "Should we set the deadline to the end of this month at 11:59 PM IST?", "End of Month 11:59 PM IST"),
        DEADLINE_CONDITIONAL: Question(DEADLINE_CONDITIONAL, "What specific date should it be due if that event hasn't happened?", "In 14 days"),
        MODE_MISSING: Question(MODE_MISSING, "How will this be paid: cash, UPI, or bank transfer?", "UPI"),
        PARTIAL_MISSING: Question(PARTIAL_MISSING, "If a partial payment is made, does that count towards reducing the balance with the deadline unchanged?", "accept_partial"),
    }

    next_q = None
    for rule in PRIORITY_ORDER:
        if rule in flags:
            next_q = questions_map.get(rule)
            break

    return flags, next_q, []
</file>

<file path="Referee/src/referee/server.py">
import os
import json
from typing import Optional, Dict, Any

from mcp.server.mcpserver import MCPServer

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
from starlette.requests import Request

from referee.parser import parse_utterance
from referee.store import init_db, create_deal, append_event, get_deal_state
from vagueterms import detect_vague_terms, BLOCKING_FLAGS
from referee.verdict import compute_verdict
from referee.links import generate_upi_link, generate_whatsapp_share_link

init_db()

mcp = MCPServer("Referee", dependencies=["mcp"])

AFFIRMATIVE_ANSWERS = {
    "yes", "y", "yeah", "yep", "yup", "ok", "okay", "sure", "correct", 
    "use default", "use defaults", "default", "sounds good", "go ahead", 
    "cool", "that works", "do it", "fine", "perfect", "sure thing"
}

@mcp.tool()
def ping() -> str:
    """A simple hello-world ping tool to verify MCP connectivity."""
    return "pong"

@mcp.tool()
def propose_deal(utterance: str) -> Dict[str, Any]:
    """Tool 1: Parses an initial handshake utterance, checks for existing counterparty names, and detects vague terms."""
    try:
        term_sheet = parse_utterance(utterance)
        slots = term_sheet.to_dict()

        counterparty = slots.get("counterparty")
        matching_parties = []

        # Check database for existing counterparties with the same name
        if counterparty:
            import referee.store as store_mod
            conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT counterparty FROM deals WHERE LOWER(counterparty) = LOWER(?)", (counterparty.strip(),))
            rows = cursor.fetchall()
            conn.close()
            if rows:
                matching_parties = [r["counterparty"] for r in rows]

        deal_id = create_deal(utterance, slots)
        open_flags, next_q, defaults_applied = detect_vague_terms(slots, utterance, matching_counterparties=matching_parties)

        next_question_str = next_q.prompt if next_q else None
        party = slots.get("counterparty") or "your friend"
        amount_inr = (slots.get("amount_paise") or 0) / 100

        if next_question_str:
            summary = f"Got it! I've noted the agreement. {next_question_str}"
        else:
            summary = f"Got it! I've recorded the deal with {party} for ₹{amount_inr:.0f}. All terms look clear and ready to lock!"

        return {
            "deal_id": deal_id,
            "slots": slots,
            "open_flags": open_flags,
            "next_question": next_question_str,
            "defaults_applied": defaults_applied,
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "I couldn't process that agreement. Could you say it again?"}

@mcp.tool()
def answer_question(deal_id: str, answer: str) -> Dict[str, Any]:
    """Tool 2: Takes an answer to a clarifying question, resolves party disambiguation, and updates deal slots."""
    try:
        state = get_deal_state(deal_id)
        if not state:
            return {"error": f"Deal {deal_id} not found", "summary": "I couldn't find an active deal to update."}

        counterparty = state.get("counterparty")
        matching_parties = []
        if counterparty:
            import referee.store as store_mod
            conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT counterparty FROM deals WHERE LOWER(counterparty) = LOWER(?)", (counterparty.strip(),))
            rows = cursor.fetchall()
            conn.close()
            if rows:
                matching_parties = [r["counterparty"] for r in rows]

        _, next_q, _ = detect_vague_terms(state, state.get("raw_utterance", ""), matching_counterparties=matching_parties)
        updates: Dict[str, Any] = {}
        answer_lower = answer.lower().strip()

        if next_q:
            rule_id = next_q.rule_id
            is_affirmative = answer_lower in AFFIRMATIVE_ANSWERS

            if rule_id == "PARTY_AMBIGUOUS":
                if is_affirmative or "same" in answer_lower:
                    updates["party_confirmed"] = True
                else:
                    # User provided a new distinguishing name (e.g., "Aman Sharma" or "Different Aman")
                    new_name = answer.strip().title()
                    updates["counterparty"] = new_name
                    updates["party_confirmed"] = True
            elif rule_id == "PARTY_PRONOUN":
                if not is_affirmative:
                    updates["counterparty"] = answer.strip().title()
            elif rule_id == "DIRECTION_UNCLEAR":
                if "borrow" in answer_lower or "i owe" in answer_lower:
                    updates["direction"] = "borrowed"
                else:
                    updates["direction"] = "lent"
            elif rule_id == "AMOUNT_FUZZY":
                try:
                    num = int("".join(filter(str.isdigit, answer)))
                    updates["amount_paise"] = num * 100
                    updates["principal_paise"] = num * 100
                except ValueError:
                    pass
            elif rule_id == "AMOUNT_UNIT":
                if is_affirmative:
                    updates["amount_confirmed"] = True
            elif rule_id in {"DEADLINE_RELATIVE", "DEADLINE_FUZZY", "DEADLINE_CONDITIONAL"}:
                if is_affirmative:
                    updates["deadline_confirmed"] = True
                elif "upi" in answer_lower or "cash" in answer_lower:
                    updates["deadline_confirmed"] = True
                    updates["payment_mode"] = "upi" if "upi" in answer_lower else "cash"
            elif rule_id == "MODE_MISSING":
                if is_affirmative or "upi" in answer_lower:
                    updates["payment_mode"] = "upi"
                elif "cash" in answer_lower:
                    updates["payment_mode"] = "cash"
                elif "bank" in answer_lower:
                    updates["payment_mode"] = "bank"
            elif rule_id == "PARTIAL_MISSING":
                if is_affirmative or "accept" in answer_lower:
                    updates["partial_policy"] = "accept_partial"
                elif "all" in answer_lower or "no" in answer_lower:
                    updates["partial_policy"] = "all_or_nothing"

        if updates:
            append_event(deal_id, "term_set", updates)

        updated_state = get_deal_state(deal_id) or {}
        
        # Re-check remaining flags
        updated_party = updated_state.get("counterparty")
        matching_updated = []
        if updated_party:
            import referee.store as store_mod
            conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT counterparty FROM deals WHERE LOWER(counterparty) = LOWER(?)", (updated_party.strip(),))
            rows = cursor.fetchall()
            conn.close()
            if rows:
                matching_updated = [r["counterparty"] for r in rows]

        remaining_flags, remaining_q, _ = detect_vague_terms(updated_state, updated_state.get("raw_utterance", ""), matching_counterparties=matching_updated)

        ready_to_lock = not any(f in BLOCKING_FLAGS for f in remaining_flags)
        next_question_str = remaining_q.prompt if remaining_q else None

        party = updated_state.get("counterparty") or "your counterparty"
        amount = (updated_state.get("principal_paise") or 0) / 100
        direction = updated_state.get("direction") or "agreed with"

        if not next_question_str and ready_to_lock:
            read_back = f"Updated! Terms set: {direction} {party} ₹{amount:.0f}. Everything looks clear and ready. Say 'lock it' to finalize!"
        elif next_question_str:
            read_back = f"Got it. {next_question_str}"
        else:
            read_back = f"Updated terms with {party}."

        return {
            "deal_id": deal_id,
            "updated_slots": updated_state,
            "remaining_flags": remaining_flags,
            "next_question": next_question_str,
            "ready_to_lock": ready_to_lock,
            "read_back": read_back,
            "summary": read_back
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to update terms."}
    
@mcp.tool()
def lock_deal(deal_id: str, confirm: bool = True) -> Dict[str, Any]:
    """Tool 3: Freezes terms and locks the deal. Returns UPI and WhatsApp sharing links."""
    try:
        if not confirm:
            return {"error": "Confirmation required to lock deal", "summary": "No problem, deal left unlocked."}

        state = get_deal_state(deal_id)
        if not state:
            return {"error": f"Deal {deal_id} not found", "summary": "Error: Deal not found."}

        open_flags, _, _ = detect_vague_terms(state, state.get("raw_utterance", ""))
        blocking_present = [f for f in open_flags if f in BLOCKING_FLAGS]

        if blocking_present:
            return {
                "error": f"Cannot lock deal with unresolved blocking flags: {blocking_present}",
                "summary": "We still need a few details before locking this deal."
            }

        append_event(deal_id, "locked", {"locked": True})

        amount_inr = (state.get("principal_paise") or 0) / 100
        party = state.get("counterparty", "friend")
        direction = state.get("direction", "lent")

        upi_link = generate_upi_link(amount_inr, note=f"Deal with {party}")
        wa_summary = f"{direction.upper()} ₹{amount_inr:.0f} with {party}."
        whatsapp_share_link = generate_whatsapp_share_link(wa_summary)
        summary = f"Locked! I've finalized the agreement with {party} for ₹{amount_inr:.0f}. You can share the WhatsApp confirmation link or use the UPI link when paying."

        return {
            "deal_id": deal_id,
            "status": "LOCKED",
            "locked_terms": state,
            "upi_link": upi_link,
            "whatsapp_share_link": whatsapp_share_link,
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to lock deal."}

@mcp.tool()
def log_payment(amount_inr: float, deal_id: Optional[str] = None, counterparty: Optional[str] = None, mode: Optional[str] = None) -> Dict[str, Any]:
    """Tool 4: Logs a payment using a FIFO waterfall across active deals for a counterparty."""
    try:
        import referee.store as store_mod
        conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
        cursor = conn.cursor()

        target_deals = []

        if deal_id:
            cursor.execute("SELECT id FROM deals WHERE id = ?", (deal_id,))
            rows = cursor.fetchall()
            target_deals = [r["id"] for r in rows]
        elif counterparty:
            cursor.execute("""
                SELECT id FROM deals 
                WHERE LOWER(counterparty) = LOWER(?) AND status != 'SETTLED'
                ORDER BY created_at ASC
            """, (counterparty.strip(),))
            rows = cursor.fetchall()
            target_deals = [r["id"] for r in rows]

            if not target_deals:
                cursor.execute("""
                    SELECT id FROM deals 
                    WHERE LOWER(counterparty) = LOWER(?)
                    ORDER BY created_at DESC LIMIT 1
                """, (counterparty.strip(),))
                row = cursor.fetchone()
                if row:
                    target_deals = [row["id"]]

        conn.close()

        if not target_deals:
            return {"error": "Deal not found", "summary": f"I couldn't find an active deal for {counterparty or 'that query'} to record that payment."}

        remaining_paise_to_apply = int(amount_inr * 100)
        events_logged = []
        last_deal_id = target_deals[0]

        for d_id in target_deals:
            if remaining_paise_to_apply <= 0:
                break
            
            last_deal_id = d_id
            st = get_deal_state(d_id, db_path=store_mod.DEFAULT_DB_PATH) or {}
            v = compute_verdict(st)
            deal_balance = v["balance_paise"]

            if deal_balance <= 0 and len(target_deals) > 1:
                continue

            paise_for_this_deal = min(remaining_paise_to_apply, deal_balance) if deal_balance > 0 else remaining_paise_to_apply
            if paise_for_this_deal > 0:
                ev_id = append_event(d_id, "payment", {"amount_paise": paise_for_this_deal, "mode": mode or "upi"}, db_path=store_mod.DEFAULT_DB_PATH)
                events_logged.append(ev_id)
                remaining_paise_to_apply -= paise_for_this_deal

        # Retrieve specific target deal balance and counterparty name
        last_st = get_deal_state(last_deal_id, db_path=store_mod.DEFAULT_DB_PATH) or {}
        last_verdict = compute_verdict(last_st)
        deal_bal_inr = last_verdict["balance_paise"] / 100
        party_name = counterparty or last_st.get("counterparty") or "counterparty"

        ledger_res = get_ledger(counterparty=party_name)
        overall_net_inr = ledger_res.get("net_balance_inr", 0)

        if overall_net_inr == 0:
            summary = f"Logged payment of ₹{amount_inr:.0f} from {party_name}. All deals with {party_name} are now fully SETTLED! Green card."
        elif overall_net_inr > 0:
            summary = f"Logged payment of ₹{amount_inr:.0f} from {party_name}. Overall remaining total owed across all active deals with {party_name} is now ₹{overall_net_inr:.0f}."
        else:
            summary = f"Logged payment of ₹{amount_inr:.0f} from {party_name}. Net total balance with {party_name}: You owe ₹{abs(overall_net_inr):.0f}."

        return {
            "events_logged": events_logged,
            "deal_id": last_deal_id,
            "amount_logged_inr": amount_inr,
            "updated_balance_inr": deal_bal_inr,
            "overall_net_balance_inr": overall_net_inr,
            "status": last_verdict["status"],
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to log payment."}

@mcp.tool()
def get_verdict(deal_id: Optional[str] = None, counterparty: Optional[str] = None) -> Dict[str, Any]:
    """Tool 5: Returns the deterministic verdict card payload and summary for a deal or counterparty."""
    try:
        party = counterparty
        target_deal_id = deal_id

        if party:
            import referee.store as store_mod
            conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM deals WHERE LOWER(counterparty) = LOWER(?) ORDER BY created_at DESC LIMIT 1", (party.strip(),))
            row = cursor.fetchone()
            conn.close()
            if row:
                target_deal_id = row["id"]

        if not target_deal_id:
            return {"error": "Deal not found", "summary": f"No active record found for {party or 'that query'}."}

        state = get_deal_state(target_deal_id)
        if not state:
            return {"error": f"Deal {target_deal_id} not found", "summary": "Error: Deal record not found."}

        verdict = compute_verdict(state)

        # If counterparty was queried, append overall context if multiple deals exist
        if party:
            ledger_info = get_ledger(counterparty=party)
            net_bal = ledger_info.get("net_balance_inr", 0)
            party_name = state.get("counterparty") or party
            if net_bal > 0:
                summary = f"Verdict for {party_name}: Outstanding balance across active deals is ₹{net_bal:.0f} ({verdict['status']})."
            elif net_bal == 0:
                summary = f"Verdict for {party_name}: Fully SETTLED. Green card."
            else:
                summary = f"Verdict for {party_name}: You owe {party_name} ₹{abs(net_bal):.0f} in total."
        else:
            summary = verdict["one_liner"]

        return {
            "deal_id": target_deal_id,
            "verdict_card": verdict,
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to compute verdict."}

@mcp.tool()
def amend_deal(deal_id: str, field: str, new_value: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Tool 6: Appends an 'amended' event modifying a deal term."""
    try:
        state = get_deal_state(deal_id)
        if not state:
            return {"error": f"Deal {deal_id} not found", "summary": "Error: Deal record not found."}

        original_val = state.get(field)
        parsed_value: Any = new_value
        if field == "amount_inr":
            field = "principal_paise"
            parsed_value = int(float(new_value) * 100)

        amendment_payload = {
            "field": field,
            "old_value": original_val,
            "new_value": parsed_value,
            "reason": reason or "User requested amendment"
        }

        event_id = append_event(deal_id, "amended", amendment_payload)
        updated_state = get_deal_state(deal_id) or {}
        party = updated_state.get("counterparty") or "deal"
        summary = f"Amended! Updated {field} for {party} to {new_value}."

        return {
            "event_id": event_id,
            "deal_id": deal_id,
            "amendment": amendment_payload,
            "updated_terms": updated_state,
            "summary": summary
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to amend deal."}

@mcp.tool()
def get_ledger(counterparty: Optional[str] = None) -> Dict[str, Any]:
    """Tool 7: Summarizes net balances across all recorded deals with an itemized person breakdown."""
    try:
        import referee.store as store_mod
        conn = store_mod.get_connection(store_mod.DEFAULT_DB_PATH)
        cursor = conn.cursor()

        if counterparty:
            cursor.execute("SELECT id FROM deals WHERE LOWER(counterparty) = LOWER(?)", (counterparty.strip(),))
        else:
            cursor.execute("SELECT id FROM deals")

        rows = cursor.fetchall()
        conn.close()

        deals_summary = []
        party_balances = {}

        for row in rows:
            d_id = row["id"]
            st = get_deal_state(d_id)
            if st:
                verdict = compute_verdict(st)
                party = st.get("counterparty") or "Unknown"
                direction = st.get("direction", "lent")
                bal = verdict["balance_paise"]
                status = verdict["status"]

                if status == "SETTLED" and not counterparty:
                    continue

                net_p = bal if direction == "lent" else -bal

                if party not in party_balances:
                    party_balances[party] = {"net_paise": 0, "status": status, "colour": verdict["colour"]}
                
                party_balances[party]["net_paise"] += net_p
                if verdict["colour"] in ("yellow", "red"):
                    party_balances[party]["status"] = status
                    party_balances[party]["colour"] = verdict["colour"]

                deals_summary.append({
                    "deal_id": d_id,
                    "counterparty": party,
                    "direction": direction,
                    "balance_inr": bal / 100,
                    "status": status,
                    "colour": verdict["colour"]
                })

        if not party_balances:
            return {
                "net_balance_inr": 0,
                "deals": [],
                "summary": "Your ledger is completely clear! No active or overdue balances found."
            }

        total_net_paise = sum(p["net_paise"] for p in party_balances.values())
        lines = ["Here is your current ledger breakdown:"]

        for name, info in party_balances.items():
            amount = info["net_paise"] / 100
            if amount > 0:
                lines.append(f"• {name} owes you ₹{amount:.0f} ({info['status']})")
            elif amount < 0:
                lines.append(f"• You owe {name} ₹{abs(amount):.0f} ({info['status']})")
            else:
                lines.append(f"• {name}: Fully settled")

        total_inr = total_net_paise / 100
        if total_inr > 0:
            lines.append(f"\nNet total: ₹{total_inr:.0f} owed to you across active deals.")
        elif total_inr < 0:
            lines.append(f"\nNet total: You owe ₹{abs(total_inr):.0f} in total.")
        else:
            lines.append(f"\nNet total balance: ₹0.")

        summary_text = "\n".join(lines)

        return {
            "net_balance_inr": total_inr,
            "deals": deals_summary,
            "summary": summary_text
        }
    except Exception as e:
        return {"error": str(e), "summary": "Failed to retrieve ledger."}

TOOLS_MAP = {
    "propose_deal": propose_deal,
    "answer_question": answer_question,
    "lock_deal": lock_deal,
    "log_payment": log_payment,
    "get_verdict": get_verdict,
    "amend_deal": amend_deal,
    "get_ledger": get_ledger
}

async def handle_simulator_tool_call(request: Request) -> JSONResponse:
    tool_name = request.path_params.get("tool_name")
    if tool_name not in TOOLS_MAP:
        return JSONResponse({"error": f"Unknown tool {tool_name}"}, status_code=404)

    body = await request.json()
    func = TOOLS_MAP[tool_name]
    res = func(**body)
    return JSONResponse(res)

async def serve_index(request: Request) -> FileResponse:
    sim_dir = os.path.join(os.path.dirname(__file__), "simulator")
    return FileResponse(os.path.join(sim_dir, "index.html"))

sim_dir_path = os.path.join(os.path.dirname(__file__), "simulator")
mcp_app = mcp.streamable_http_app()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp_app.router.lifespan_context(app):
        yield

app = Starlette(
    routes=[
        Route("/", endpoint=serve_index),
        Route("/api/tool/{tool_name}", endpoint=handle_simulator_tool_call, methods=["POST"]),
        Mount("/simulator", StaticFiles(directory=sim_dir_path)),
        Mount("/", app=mcp_app),
    ],
    lifespan=lifespan
)
</file>

<file path="Referee/ROADMAP.md">
# ROADMAP.md: Referee build tracker (for the AI assistant)

> **AI: read this file FIRST, every session, before doing anything else.**
> Then read `Referee_Project_Overview.md` sections 4, 5 and 9 if you have not in this session.
> This file is the single source of truth for "where are we". Update it before you stop.

---

## 0. START HERE (update this block every session)

```
CURRENT PHASE:      3 (Polish)
CURRENT TASK:       P3.1 Bedrock parser (Amazon Nova + regex fallback)
LAST COMPLETED:     Phase 2 (Tools 1-7, Links, Simulator UI, MCP Inspector protocol)
LAST SESSION NOTE:  Phase 2 verified green! All 7 MCP tools live over Streamable HTTP (/mcp). Simulator UI with Web Speech API & JSON-RPC traffic panel fully functional. Ready to add Bedrock parser fallback and polish docs.
BLOCKERS:           none
LAST UPDATED:       21 Oct 2026 10:50 PM IST
```

### Session protocol
1. Read this file. Go to `CURRENT TASK`. Do NOT start from scratch or re-plan.
2. Run `pytest` (once tests exist) to confirm the baseline is green before changing anything.
3. Work tasks in order. Tick `[x]` only when the task's **Done when** is actually true (run it, don't assume).
4. After each task: commit with a clear message, update `START HERE`, then move on.
5. Before stopping or when context is getting long: fill `LAST SESSION NOTE` with exact next step.
6. Anything annoying with a tool/SDK/docs: append one raw line to `FRICTION_NOTES.md` (format in section 7). Never invent entries.
7. If a task is stuck for more than 30 minutes: write the exact error in Blockers, propose the cut, ask the builder.

### Hard rules (from the overview, section 9)
- Do not add scope outside the overview sections 4 and 7. Ask first.
- Money = integer paise. Datetimes timezone-aware, default `Asia/Kolkata`.
- Detector and verdict engine are pure functions, unit-tested, no network. The model never decides a verdict.
- No secrets in git. Use env vars and `.env.example`.
- Be honest in README and video about what is simulated (Alexa+ host, UPI verification).
- Original work only. Do not copy other entries.

---

## 1. Timeline (IST) and cut line

| When | Goal |
|---|---|
| Wed 21 Oct evening (optional head start) | Phase 0 |
| Thu 22 Oct, to ~2 PM | Phase 1 (detector + tools 1-3) |
| Thu 22 Oct, 2 PM to ~10 PM | Phase 2 (tools 4-7, links, simulator) |
| Fri 23 Oct, 8 AM to 12 PM | Phase 3 (polish). **FEATURE FREEZE 12 PM** |
| Fri 23 Oct, 12 PM to 6 PM | Phase 4 (video, docs, Devpost, **SUBMIT by 6 PM**) |
| Fri 6 PM to Sat 12:30 AM | Buffer only. Fix broken links/access. No new work |

**Hard deadline:** Sat 24 Oct 12:30 AM IST (Fri 23 Oct 12:00 PM PT). Submissions cannot be edited after.

**CUT LINE (binding):** If tools 1-5 plus detector do not work by Thursday night, drop tools 6-7 and the fancy card. A polished 5-tool demo beats a shaky 7-tool one.

---

## 2. Phase 0: Setup

- [ ] **P0.1 Repo.** Create public GitHub repo `referee`, add MIT `LICENSE` in root, README stub, `.gitignore`, `.env.example`. First commit dated inside the window.
  - Done when: repo is public and the License shows in the GitHub About section.
- [ ] **P0.2 Project skeleton.** `pyproject.toml`, `src/referee/`, `tests/`, `docs/`, `FRICTION_NOTES.md` (empty with header). Python 3.11+, venv, `pip install "mcp[cli]" pytest python-dateutil`.
  - Done when: `pytest` runs (even with zero tests) and `python -c "import mcp"` works.
- [ ] **P0.3 Hello-world MCP.** FastMCP server, one `ping` tool, `transport="streamable-http"`, endpoint `/mcp`.
  - Done when: MCP Inspector (`npx @modelcontextprotocol/inspector`) connects and lists `ping`.
- [ ] **P0.4 Protocol version check.** In Inspector confirm `initialize` negotiates **2025-11-25 or later**. If older, upgrade the SDK. Log any trouble in FRICTION_NOTES.
  - Done when: the negotiated version is written here: `______`.
- [ ] **P0.5 Devpost + AWS.** Join the hackathon on Devpost (builder does this). Request Bedrock model access (builder does this; check the console for the Nova model ID in the region). Builder checks for free-tier credit.
  - Done when: builder confirms. If Bedrock is not available, continue with the regex fallback only.
- [ ] **P0.6 Second repo.** Create public repo `vagueterms` (MIT, created inside the window) with `pyproject.toml` and README stub.
  - Done when: `pip install -e ../vagueterms` works from the referee venv.

---

## 3. Phase 1: Core (detector + tools 1-3)

- [ ] **P1.1 Term sheet model.** Dataclass/pydantic `TermSheet` with slots from overview 4.2 (`direction, counterparty, amount_paise, currency, deadline_ts, payment_mode, partial_policy, purpose`).
- [ ] **P1.2 Detector in `vagueterms`.** Implement the 10 rules from overview 4.3 as pure functions: `DEADLINE_RELATIVE, DEADLINE_FUZZY, DEADLINE_CONDITIONAL, AMOUNT_FUZZY, AMOUNT_UNIT, PARTY_PRONOUN, PARTY_AMBIGUOUS, DIRECTION_UNCLEAR, MODE_MISSING, PARTIAL_MISSING`.
  - Priority order for questions: direction, counterparty, amount, deadline, mode, partial.
  - Max 3 questions per deal, one per turn, every question has a default. Then apply defaults and report them.
  - Blocking flags (deal cannot lock): `DIRECTION_UNCLEAR`, `PARTY_PRONOUN`, `AMOUNT_FUZZY`.
  - Done when: `pytest` green for every rule with positive and negative cases, plus the "today is Friday" and week-boundary date edge cases.
- [ ] **P1.3 Parser.** `parser.py`: regex + `dateparser`/`dateutil` fallback first (this is the guaranteed path). Bedrock structured-JSON parse is added in P3.x, behind the same interface.
  - Done when: "I lent Aman 1,500, he'll pay Friday" yields direction=lent, counterparty=Aman, amount_paise=150000, deadline flagged relative.
- [ ] **P1.4 Store.** `store.py`: SQLite, tables `deals` and `deal_events` (overview 4.5), append-only. Balance/status derived by folding events.
  - Done when: tests prove events are never updated and the state folds correctly.
- [ ] **P1.5 Tool 1 `propose_deal`.** Returns `deal_id, slots, open_flags[], next_question, defaults_applied[]`, plus `structuredContent` and a speakable `summary`.
- [ ] **P1.6 Tool 2 `answer_question`.** Updates slots, returns remaining flags, next question or `ready_to_lock: true`, and read-back text. Supports "use defaults".
- [ ] **P1.7 Tool 3 `lock_deal`.** Requires `confirm: true`; refuses if blocking flags remain. Freezes terms in a `locked` event. Returns `upi_link`, `whatsapp_share_link`, `locked_at` (links can be stubbed until P2.4).
  - **PHASE 1 DONE when:** in MCP Inspector, `propose_deal` -> `answer_question` -> `lock_deal` works end to end, and detector tests are green. Commit and tag `phase1`.

---

## 4. Phase 2: Rest (tools 4-7, links, simulator)

- [ ] **P2.1 Verdict engine `verdict.py`.** Pure function per overview 4.6: `paid, balance, status (OPEN/PARTIALLY_PAID/SETTLED/OVERDUE), days_overdue, colour` (green / neutral / yellow 1-7 days / red >7). `all_or_nothing` records partials without changing status. Thresholds are constants.
  - Done when: tests cover each status, each colour boundary (day 0, 1, 7, 8), amendments, and all_or_nothing.
- [ ] **P2.2 Tool 4 `log_payment`.** By `deal_id` or `counterparty` (use `PARTY_AMBIGUOUS` if two match). Returns updated balance, status, event id.
- [ ] **P2.3 Tool 5 `get_verdict`.** Returns the verdict card payload and one-liner, e.g. "Verdict: Aman owes ₹500. Deadline passed 2 days ago. Yellow card."
  - **CORE DONE when P2.1-P2.3 pass in Inspector. Check the cut line (section 1) now.**
- [ ] **P2.4 Links `links.py`.** UPI link (`upi://pay?pa=...&pn=...&am=...&cu=INR&tn=...`) from env `PAYEE_VPA`; omit if not set. WhatsApp `https://wa.me/?text=<urlencoded>`. Unit-tested.
- [ ] **P2.5 Tool 6 `amend_deal`** (only if the cut line allows). Appends an `amended` event; never edits the original. Returns original vs current terms and full history.
- [ ] **P2.6 Tool 7 `get_ledger`** (only if the cut line allows). Per-person net balances with status.
- [ ] **P2.7 Simulator.** `src/referee/simulator/` single `index.html` + `app.js`: chat box, mic via Web Speech API, intent -> MCP tool calls (rule-based is fine), **side panel showing raw MCP JSON-RPC traffic**, verdict card (green / neutral / yellow / red). Mount next to `/mcp`.
  - Done when: the full demo story runs start to finish: lend -> questions -> lock -> payment -> amend -> new session -> verdict -> ledger.
- [ ] **P2.8 Seed data** for the demo, clearly labelled "seed data" in code and README.

---

## 5. Phase 3: Polish (feature freeze 12 PM IST Fri)

- [ ] **P3.1 Bedrock parser.** Utterance -> term-sheet JSON via an Amazon Nova model; same interface as the regex parser; automatic fallback to regex on any error. Model never decides verdicts.
  - Done when: works with creds, and the demo still works with Bedrock disabled. If access is unavailable, skip and say so honestly in the docs.
- [ ] **P3.2 Security + errors.** `Origin` check, optional bearer token on `/mcp`, friendly tool errors, no stack traces to the client.
- [ ] **P3.3 Tunnel/deploy.** `cloudflared` tunnel (or free host) so `/mcp` is reachable over HTTPS. Note any problems in FRICTION_NOTES.
- [ ] **P3.4 Card styling** and a visual check on a phone-width screen.
- [ ] **P3.5 README.** What/why, setup, run, test, tools table, **real vs simulated**, "not legal advice / no payment verification", license.
- [ ] **P3.6 `docs/ARCHITECTURE.md`** (short, one diagram).
- [ ] **P3.7 Full test pass.** `pytest` green. Inspector shows the tools and protocol >= 2025-11-25.
- [ ] **P3.8 FEATURE FREEZE at 12 PM IST.** Only bug fixes after this.

---

## 6. Phase 4: Ship (submit by 6 PM IST Fri 23 Oct)

- [ ] **P4.1 Demo video** (under 3:00, English, public on YouTube, no copyrighted music). Follow overview section 10. First 20 seconds: finished yellow-card verdict. Say clearly what is simulated.
- [ ] **P4.2 Friction log.** Expand `FRICTION_NOTES.md` into `docs/FRICTION_LOG.md` using the template in the overview 8.1. Ask the builder for any missing details. **Do not invent anything not in the notes.** Roughly 6-10 real entries.
- [ ] **P4.3 Product feedback** (`docs/PRODUCT_FEEDBACK.md`): mandatory, covers every tool/API/SDK used, which AWS services and how, what worked, what did not, would you build again.
- [ ] **P4.4 `vagueterms` repo polished:** README with examples, tests green, `pip install -e .` works, imported by Referee.
- [ ] **P4.5 Devpost form:** description, repo URL, video URL, Track = Alexa+, mini challenges = AWS Builder and Open Source (note: only one mini-challenge prize can be won), Open Source fields (contribution URL, repo URL, GitHub username, description), feedback, friction log. Re-check the Rules page for any changes.
- [ ] **P4.6 Final checks.** Repo public with the visible MIT license, first commit inside the window (31 Aug-23 Oct), no secrets in git history, links open while logged out.
- [ ] **P4.7 SUBMIT** and save the confirmation. Target: before 6 PM IST.

---

## 7. FRICTION_NOTES.md format (raw, one line each)

`Thu 3:40pm | Inspector | session id lost after restart, no clear error`

Save exact error text and screenshots in `docs/friction/`. Only log what really happened.

---

## 8. Decision log (append, newest last)

| Date/time | Decision | Why |
|---|---|---|
| | | |

## 9. Blockers log

| Date/time | Blocker (exact error) | Proposed cut / workaround | Status |
|---|---|---|---|
| | | | |

## 10. Out of scope (do not build)

User accounts, counterparty app, notifications, group splits, payment verification, OCR, OAuth/account linking, anything on-chain.
</file>

</files>
