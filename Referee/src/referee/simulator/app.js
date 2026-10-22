// Referee — Alexa+ simulator.
// This page is a real MCP client: it talks to the server's /mcp endpoint using the
// Streamable HTTP transport (initialize -> notifications/initialized -> tools/list -> tools/call).
// The "MCP Traffic" panel shows the actual JSON-RPC messages that go over the wire.

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
const protoPill = document.getElementById("protoPill"); // optional element

// ---------------------------------------------------------------------------
// MCP client (Streamable HTTP)
// ---------------------------------------------------------------------------

const MCP_ENDPOINT = "/mcp";
const CLIENT_PROTOCOL_VERSION = "2025-11-25";

let mcpSessionId = null;
let mcpProtocolVersion = null;
let mcpReady = null; // promise for the handshake
let mcpReqId = 0;
let mcpConnected = false;

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function setProtoPill(text) {
  if (protoPill) protoPill.textContent = text;
}

function logFrame(kind, label, payload, meta) {
  rpcCounter += kind === "req" ? 1 : 0;
  if (rpcCount) rpcCount.innerText = `${rpcCounter} requests`;

  const block = document.createElement("div");
  block.className = "rpc-block";

  const head = document.createElement("div");
  head.className = `rpc-type ${kind === "req" ? "rpc-req" : "rpc-res"}`;
  const left = document.createElement("span");
  left.textContent = kind === "req" ? "Request" : "Response";
  const right = document.createElement("span");
  right.textContent = meta ? `${label} · ${meta}` : label;
  head.appendChild(left);
  head.appendChild(right);

  block.appendChild(head);
  block.appendChild(document.createTextNode(JSON.stringify(payload, null, 2)));
  trafficLog.appendChild(block);
  setTimeout(() => {
    trafficLog.scrollTop = trafficLog.scrollHeight;
  }, 50);
}

// The server answers a POST with either plain JSON or a short text/event-stream.
async function readJsonRpc(res, id) {
  const contentType = res.headers.get("content-type") || "";
  const text = await res.text();
  if (!text) return null;

  if (contentType.includes("text/event-stream")) {
    const messages = [];
    for (const block of text.split(/\r?\n\r?\n/)) {
      const dataLines = block
        .split(/\r?\n/)
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart());
      if (dataLines.length) {
        try {
          messages.push(JSON.parse(dataLines.join("\n")));
        } catch (e) {
          /* ignore non-JSON events */
        }
      }
    }
    return messages.find((m) => m.id === id) || messages[messages.length - 1] || null;
  }

  try {
    return JSON.parse(text);
  } catch (e) {
    return { error: { code: -32700, message: `Non-JSON response from server: ${text.slice(0, 120)}` } };
  }
}

function mcpHeaders() {
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream"
  };
  if (mcpSessionId) headers["Mcp-Session-Id"] = mcpSessionId;
  if (mcpProtocolVersion) headers["MCP-Protocol-Version"] = mcpProtocolVersion;
  return headers;
}

async function mcpRequest(method, params) {
  const id = ++mcpReqId;
  const message = { jsonrpc: "2.0", id, method, params };
  logFrame("req", method, message);

  const hadSession = Boolean(mcpSessionId);
  const res = await fetch(MCP_ENDPOINT, {
    method: "POST",
    headers: mcpHeaders(),
    body: JSON.stringify(message)
  });

  const sid = res.headers.get("mcp-session-id");
  if (sid) mcpSessionId = sid;

  const reply = await readJsonRpc(res, id);
  const meta = `HTTP ${res.status}${sid ? " · session " + sid.slice(0, 8) : ""}`;
  logFrame("res", method, reply || { note: "empty body" }, meta);

  if (res.status === 404 && hadSession) {
    const err = new Error("MCP session expired");
    err.sessionExpired = true;
    throw err;
  }
  if (!reply) throw new Error(`Empty response from /mcp (HTTP ${res.status})`);
  if (reply.error) throw new Error(reply.error.message || "MCP error");
  return reply.result;
}

async function mcpNotify(method, params) {
  const message = { jsonrpc: "2.0", method };
  if (params) message.params = params;
  logFrame("req", method, message);
  const res = await fetch(MCP_ENDPOINT, {
    method: "POST",
    headers: mcpHeaders(),
    body: JSON.stringify(message)
  });
  await res.text();
  logFrame("res", method, { note: "notification accepted, no body" }, `HTTP ${res.status}`);
}

function connectMcp() {
  if (mcpReady) return mcpReady;

  mcpReady = (async () => {
    mcpSessionId = null;
    mcpProtocolVersion = null;
    mcpConnected = false;
    setProtoPill("Connecting to /mcp…");

    const init = await mcpRequest("initialize", {
      protocolVersion: CLIENT_PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: { name: "referee-simulator", version: "0.1.0" }
    });
    mcpProtocolVersion = init.protocolVersion;

    await mcpNotify("notifications/initialized");

    try {
      await mcpRequest("tools/list", {});
    } catch (e) {
      console.warn("tools/list failed", e);
    }

    mcpConnected = true;
    setProtoPill(`MCP ${mcpProtocolVersion} · Streamable HTTP`);
    updateStatusBadge(Boolean(currentDealId));
  })();

  mcpReady.catch((err) => {
    console.error("MCP connection failed", err);
    mcpReady = null;
    mcpConnected = false;
    setProtoPill("MCP unreachable");
    updateStatusBadge(false);
  });

  return mcpReady;
}

// Normalise a tools/call result into the plain object our tools return.
function unwrapToolResult(result) {
  if (!result) return { error: "Empty MCP result", summary: "The server returned an empty result." };

  let data = null;
  let text = null;

  if (Array.isArray(result.content)) {
    const part = result.content.find((c) => c.type === "text");
    if (part) text = part.text;
  }

  const sc = result.structuredContent;
  if (sc && typeof sc === "object") {
    const keys = Object.keys(sc);
    data = keys.length === 1 && keys[0] === "result" && sc.result && typeof sc.result === "object" ? sc.result : sc;
  } else if (text) {
    try {
      data = JSON.parse(text);
    } catch (e) {
      data = { summary: text };
    }
  }

  if (!data) data = {};
  if (result.isError) {
    return { error: data.error || text || "Tool error", summary: data.summary || text || "The tool reported an error." };
  }
  return data;
}

async function callMCPTool(toolName, args, retried = false) {
  try {
    await connectMcp();
    const result = await mcpRequest("tools/call", { name: toolName, arguments: args });
    return unwrapToolResult(result);
  } catch (err) {
    if (err.sessionExpired && !retried) {
      mcpReady = null;
      return callMCPTool(toolName, args, true);
    }
    console.error("Tool execution failed", err);
    return {
      error: err.message || "MCP error",
      summary: "I couldn't reach the Referee MCP server at /mcp. Is it running?"
    };
  }
}

// ---------------------------------------------------------------------------
// Chat UI
// ---------------------------------------------------------------------------

function sendSample(text) {
  userInput.value = text;
  handleUserMessage(text);
}

function appendMessage(sender, text, verdictCard = null) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `msg ${sender}`;

  const textContainer = document.createElement("div");
  const lines = String(text == null ? "" : text).split("\n");
  lines.forEach((line, i) => {
    if (i > 0) textContainer.appendChild(document.createElement("br"));
    textContainer.appendChild(document.createTextNode(line));
  });
  msgDiv.appendChild(textContainer);

  if (verdictCard) {
    const colour = ["green", "yellow", "red", "neutral"].includes(verdictCard.colour) ? verdictCard.colour : "neutral";
    const card = document.createElement("div");
    card.className = `verdict-card ${colour}`;
    card.innerHTML = `
      <div class="verdict-header">
        <span>${escapeHtml(verdictCard.counterparty)}</span>
        <span class="status-pill">${escapeHtml(verdictCard.status)}</span>
      </div>
      <div class="verdict-body">
        <span>Balance: <strong>₹${(Number(verdictCard.balance_paise) / 100).toFixed(0)}</strong></span>
        <span>Overdue: <strong>${Number(verdictCard.days_overdue)} day(s)</strong></span>
      </div>
    `;
    msgDiv.appendChild(card);
  }

  chatHistory.appendChild(msgDiv);
  setTimeout(() => {
    chatHistory.scrollTop = chatHistory.scrollHeight;
  }, 50);
}

function extractName(text) {
  const ignore = new Set([
    "paid", "payed", "repaid", "received", "for", "deal", "rs", "inr", "rupees", "i", "lent",
    "borrowed", "he", "she", "verdict", "status", "did", "pay", "a", "the", "its", "it's",
    "different", "another", "same", "person", "one", "who", "owes", "me", "what", "how",
    "much", "does", "owe", "cancel", "nevermind", "sounds", "good", "yep", "yeah", "sure",
    "cool", "do", "it", "lock", "confirm", "now", "which", "which?", "who?", "where"
  ]);
  const words = text.replace(/[^a-zA-Z\s]/g, "").split(/\s+/);
  for (const w of words) {
    if (w.length > 1 && !ignore.has(w.toLowerCase())) {
      return w;
    }
  }
  return null;
}

function updateStatusBadge(isDraft = false) {
  const statusPill = document.getElementById("statusPill");
  if (!statusPill) return;
  if (isDraft) {
    statusPill.className = "pill active-draft";
    statusPill.innerHTML = `<span class="dot"></span>Drafting agreement...`;
  } else {
    statusPill.className = "pill";
    statusPill.innerHTML = `<span class="dot"></span>${mcpConnected ? "MCP server connected" : "MCP server not connected"}`;
  }
}

async function handleUserMessage(text) {
  if (!text || !text.trim()) return;
  const trimmed = text.trim();
  appendMessage("user", trimmed);
  userInput.value = "";

  const lower = trimmed.toLowerCase();

  // Intent 0: Conversational Pleasantries
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
    updateStatusBadge(false);
    appendMessage("alexa", "Cancelled active deal proposal. How else can I help?");
    return;
  }

  // Intent 2: General Ledger Query
  const isLedgerQuery = lower.includes("ledger") ||
                        /\bwho\s+owes\s+me\b/i.test(lower) ||
                        /\bwhat\s+do\s+i\s+owe\b/i.test(lower) ||
                        /\boverall\s+balance\b/i.test(lower);

  if (isLedgerQuery) {
    currentDealId = null;
    updateStatusBadge(false);
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
    currentDealId = null;
    updateStatusBadge(false);
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
      appendMessage("alexa", res.summary || `No active record found for ${detectedName || "that query"}.`);
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
        updateStatusBadge(false);
      }
    } else {
      appendMessage("alexa", "There is no active deal to lock right now.");
    }
    return;
  }

  // Intent 5: Log Payment
  const isPaymentIntent = /\b(paid|payed|repaid|received|sent|transferred)\b/i.test(lower);
  if (isPaymentIntent) {
    currentDealId = null;
    updateStatusBadge(false);

    // Strip commas first so "1,500" becomes "1500"
    const cleanText = trimmed.replace(/,/g, "");
    const numMatch = cleanText.match(/\d+(?:\.\d+)?/);
    const amount = numMatch ? parseFloat(numMatch[0]) : 0;
    const detectedName = extractName(trimmed);

    let paymentArgs = { amount_inr: amount };

    if (detectedName) {
      paymentArgs.counterparty = detectedName;
    } else if (lastLockedDealId) {
      paymentArgs.deal_id = lastLockedDealId;
    } else if (lastCounterparty) {
      paymentArgs.counterparty = lastCounterparty;
    }

    const res = await callMCPTool("log_payment", paymentArgs);
    appendMessage("alexa", res.summary);
    return;
  }

 // Intent 6: Answer Clarifying Question for Active Deal Proposal
  const isNewProposalUtterance = /\b(i lent|i owe|lent|borrowed|gave|took)\b/i.test(trimmed);

  if (currentDealId && !isNewProposalUtterance) {
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
    updateStatusBadge(true);
    if (res.slots && res.slots.counterparty) {
      lastCounterparty = res.slots.counterparty;
    }
    appendMessage("alexa", res.summary);
  } else {
    appendMessage("alexa", res.summary || "I couldn't process that handshake deal. Could you rephrase?");
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

// Open the MCP session as soon as the page loads so the handshake is visible in the panel.
connectMcp().catch(() => {});