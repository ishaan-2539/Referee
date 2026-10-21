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