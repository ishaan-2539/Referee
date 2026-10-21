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

function appendMessage(sender, text, verdictCard = null) {
  const msgDiv = document.createElement("div");
  msgDiv.className = `msg ${sender}`;
  msgDiv.innerText = text;

  if (verdictCard) {
    const card = document.createElement("div");
    card.className = `verdict-card ${verdictCard.colour}`;
    card.innerHTML = `
      <div class="verdict-header">
        <span>${verdictCard.counterparty}</span>
        <span>${verdictCard.status}</span>
      </div>
      <div class="verdict-body">
        Balance: ₹${(verdictCard.balance_paise / 100).toFixed(0)} | Overdue: ${verdictCard.days_overdue} day(s)
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
  reqBlock.innerHTML = `<div class="rpc-type rpc-req">➔ REQUEST [${method}]</div>${JSON.stringify(reqFrame, null, 2)}`;

  const resBlock = document.createElement("div");
  resBlock.className = "rpc-block";
  resBlock.innerHTML = `<div class="rpc-type rpc-res">⬅ RESPONSE</div>${JSON.stringify(resFrame, null, 2)}`;

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
  const ignore = new Set(["paid", "received", "for", "deal", "rs", "inr", "rupees", "i", "lent", "borrowed", "he", "she", "verdict", "status", "did", "pay", "a", "the"]);
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

  // Scenario 1: Lock Deal
  if (lower.includes("lock") || lower.includes("confirm")) {
    const dealToLock = currentDealId || lastLockedDealId;
    if (dealToLock) {
      const res = await callMCPTool("lock_deal", { deal_id: dealToLock, confirm: true });
      if (res.error) {
        appendMessage("alexa", res.summary || res.error);
      } else {
        let linksText = `\n\n🔗 WhatsApp Share: ${res.whatsapp_share_link}`;
        if (res.upi_link) {
          linksText += `\n💳 UPI Link: ${res.upi_link}`;
        } else {
          linksText += `\n💳 UPI Link: (Set PAYEE_VPA in .env to generate UPI links)`;
        }
        appendMessage("alexa", `${res.summary}${linksText}`);
        lastLockedDealId = dealToLock;
        currentDealId = null; // Unset active deal once locked
      }
    } else {
      appendMessage("alexa", "There is no active deal to lock right now.");
    }
    return;
  }

  // Scenario 2: Log Payment
  if (lower.includes("paid") || lower.includes("received")) {
    const numMatch = trimmed.match(/\d+/);
    const amount = numMatch ? parseFloat(numMatch[0]) : 0;
    const detectedName = extractName(trimmed) || lastCounterparty;
    
    const res = await callMCPTool("log_payment", { 
      amount_inr: amount, 
      deal_id: currentDealId || lastLockedDealId,
      counterparty: detectedName
    });
    appendMessage("alexa", res.summary);
    return;
  }

  // Scenario 3: Verdict Query
  if (lower.includes("verdict") || lower.includes("status") || lower.includes("did he pay") || lower.includes("did she pay")) {
    const detectedName = extractName(trimmed) || lastCounterparty;
    const res = await callMCPTool("get_verdict", { 
      deal_id: currentDealId || lastLockedDealId,
      counterparty: detectedName
    });
    if (res.verdict_card) {
      appendMessage("alexa", res.summary, res.verdict_card);
    } else {
      appendMessage("alexa", res.summary);
    }
    return;
  }

  // Scenario 4: Ledger Query
  if (lower.includes("ledger") || lower.includes("who owes me")) {
    const res = await callMCPTool("get_ledger", {});
    appendMessage("alexa", res.summary);
    return;
  }

  // Scenario 5: Answer Question for Current Active Deal
  if (currentDealId) {
    const res = await callMCPTool("answer_question", { deal_id: currentDealId, answer: trimmed });
    if (res.updated_slots && res.updated_slots.counterparty) {
      lastCounterparty = res.updated_slots.counterparty;
    }
    appendMessage("alexa", res.read_back || res.summary);
    return;
  }

  // Scenario 6: Propose New Deal
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