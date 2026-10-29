const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ── State ──
let state = "IDLE"; // IDLE | RESEARCHING | CLARIFYING | COMPLETE
let sessionId = null;
let currentMode = "code";
let eventSource = null;

// ── Elements ──
const queryInput = $("#query-input");
const runBtn = $("#run-btn");
const clarifyPanel = $("#clarify-panel");
const clarifyQuestions = $("#clarify-questions");
const progressTracker = $("#progress-tracker");
const progressLog = $("#progress-log");
const reportContainer = $("#report-container");
const reportContent = $("#report-content");
const statsFooter = $("#stats-footer");

// ── Mode Selector ──
$$(".mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        if (state !== "IDLE") return;
        $$(".mode-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentMode = btn.dataset.mode;
    });
});

// ── Examples ──
$$(".example-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        queryInput.value = btn.textContent;
        startResearch();
    });
});

// ── Query Submit ──
runBtn.addEventListener("click", startResearch);
queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") startResearch();
});

// ── Clarification ──
$("#submit-answers").addEventListener("click", submitClarification);
$("#skip-answers").addEventListener("click", () => submitClarification(true));

// ── Downloads & Email ──
$("#download-pdf").addEventListener("click", () => {
    if (sessionId) window.open(`/api/research/${sessionId}/report/pdf`, "_blank");
});

$("#download-md").addEventListener("click", () => {
    if (sessionId) window.open(`/api/research/${sessionId}/report/md`, "_blank");
});

$("#email-btn").addEventListener("click", () => {
    $("#email-form").classList.toggle("hidden");
});

$("#send-email").addEventListener("click", async () => {
    const email = $("#email-input").value.trim();
    if (!email || !sessionId) return;
    const res = await fetch(`/api/research/${sessionId}/email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: email }),
    });
    if (res.ok) {
        $("#email-form").classList.add("hidden");
        addLog("Email sent successfully", "status");
    }
});

// ── Core Functions ──

async function startResearch() {
    const query = queryInput.value.trim();
    if (!query || state !== "IDLE") return;

    setState("RESEARCHING");
    resetUI();

    try {
        const res = await fetch("/api/research", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query, mode: currentMode }),
        });

        if (!res.ok) {
            const err = await res.json();
            addLog(err.detail || "Failed to start research", "error");
            setState("IDLE");
            return;
        }

        const data = await res.json();
        sessionId = data.session_id;
        connectSSE();
    } catch (e) {
        addLog("Connection failed: " + e.message, "error");
        setState("IDLE");
    }
}

function connectSSE() {
    if (eventSource) eventSource.close();

    eventSource = new EventSource(`/api/research/${sessionId}/stream`);

    eventSource.addEventListener("status", (e) => {
        const data = JSON.parse(e.data);
        addLog(data.message, "status");
    });

    eventSource.addEventListener("progress", (e) => {
        const data = JSON.parse(e.data);
        addLog(data.message, "status");
    });

    eventSource.addEventListener("clarify", (e) => {
        const data = JSON.parse(e.data);
        showClarification(data.data.questions);
    });

    eventSource.addEventListener("complete", (e) => {
        const data = JSON.parse(e.data);
        showReport(data.data.report);
        eventSource.close();
        setState("COMPLETE");
    });

    eventSource.addEventListener("error", (e) => {
        try {
            const data = JSON.parse(e.data);
            addLog(data.message, "error");
            if (!data.data?.recoverable) {
                eventSource.close();
                setState("IDLE");
            }
        } catch {
            // SSE connection error
            if (eventSource.readyState === EventSource.CLOSED) {
                addLog("Connection lost", "error");
                setState("IDLE");
            }
        }
    });
}

function showClarification(questions) {
    setState("CLARIFYING");
    clarifyQuestions.innerHTML = "";

    questions.forEach((q, i) => {
        const div = document.createElement("div");
        div.className = "clarify-question";
        div.innerHTML = `
            <label>${q.question}</label>
            <div class="purpose">${q.purpose}</div>
            <input type="text" id="answer-${i}" data-question="${q.question}" placeholder="Your answer...">
        `;
        clarifyQuestions.appendChild(div);
    });

    clarifyPanel.classList.remove("hidden");
}

async function submitClarification(skip = false) {
    const answers = {};
    if (!skip) {
        clarifyQuestions.querySelectorAll("input").forEach((input) => {
            if (input.value.trim()) {
                answers[input.dataset.question] = input.value.trim();
            }
        });
    }

    clarifyPanel.classList.add("hidden");
    setState("RESEARCHING");

    await fetch(`/api/research/${sessionId}/clarify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
    });
}

function showReport(report) {
    reportContent.innerHTML = markdownToHTML(report.markdown);
    reportContainer.classList.remove("hidden");

    const stats = [];
    if (report.total_tokens_used) stats.push(`${report.total_tokens_used.toLocaleString()} tokens`);
    if (report.total_duration_seconds) stats.push(`${report.total_duration_seconds.toFixed(1)}s`);
    if (report.num_sources_scraped) stats.push(`${report.num_sources_scraped} sources`);
    if (report.critique_score) stats.push(`Score: ${report.critique_score.toFixed(1)}/10`);
    stats.push(`Mode: ${report.orchestration_mode}`);

    statsFooter.textContent = stats.join(" | ");
    statsFooter.classList.remove("hidden");
}

// ── Helpers ──

function setState(newState) {
    state = newState;
    runBtn.disabled = state !== "IDLE";

    if (state === "RESEARCHING" || state === "CLARIFYING") {
        progressTracker.classList.remove("hidden");
    }
}

function resetUI() {
    progressLog.innerHTML = "";
    reportContent.innerHTML = "";
    reportContainer.classList.add("hidden");
    clarifyPanel.classList.add("hidden");
    statsFooter.classList.add("hidden");
    progressTracker.classList.remove("hidden");
}

function addLog(message, type = "status") {
    const entry = document.createElement("div");
    entry.className = `log-entry${type === "error" ? " error" : ""}`;
    const time = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-time">${time}</span>${message}`;
    progressLog.appendChild(entry);
    progressLog.scrollTop = progressLog.scrollHeight;
}

function markdownToHTML(md) {
    if (!md) return "";
    let html = md
        .replace(/^### (.*$)/gm, "<h3>$1</h3>")
        .replace(/^## (.*$)/gm, "<h2>$1</h2>")
        .replace(/^# (.*$)/gm, "<h1>$1</h1>")
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>")
        .replace(/`(.*?)`/g, "<code>$1</code>")
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
        .replace(/^> (.*$)/gm, "<blockquote>$1</blockquote>")
        .replace(/^- (.*$)/gm, "<li>$1</li>")
        .replace(/^\d+\. (.*$)/gm, "<li>$1</li>");

    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);

    // Paragraphs
    html = html
        .split("\n\n")
        .map((block) => {
            block = block.trim();
            if (!block) return "";
            if (block.startsWith("<h") || block.startsWith("<ul") || block.startsWith("<blockquote") || block.startsWith("<pre")) {
                return block;
            }
            return `<p>${block}</p>`;
        })
        .join("\n");

    return html;
}
