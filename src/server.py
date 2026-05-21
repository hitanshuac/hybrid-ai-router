import os
import time
import asyncio
import logging
import duckdb
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union

from src.router import classify_and_route
from src.health import provider_statuses, stats, health_ping_loop

from src.circuit_breaker import get_circuit_status

logger = logging.getLogger("server")

app = FastAPI(title="Hybrid AI Router API")

# ============================================================
# DuckDB Telemetry — v2.4.0
# ============================================================
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(_DB_DIR, exist_ok=True)
_DB_PATH = os.path.join(_DB_DIR, "pipeline_metrics.db")

def _init_metrics_db():
    """Initialize the DuckDB metrics database with WAL mode and memory cap."""
    try:
        con = duckdb.connect(_DB_PATH)
        con.execute("PRAGMA memory_limit='256MB'")
        con.execute("CREATE SEQUENCE IF NOT EXISTS compaction_log_id_seq START 1")
        con.execute("""
            CREATE TABLE IF NOT EXISTS compaction_log (
                id INTEGER PRIMARY KEY DEFAULT(nextval('compaction_log_id_seq')),
                timestamp TEXT NOT NULL,
                raw_tokens INTEGER NOT NULL,
                compact_tokens INTEGER NOT NULL,
                tokens_saved INTEGER NOT NULL,
                savings_pct REAL NOT NULL,
                messages_dropped INTEGER NOT NULL,
                prefixes_stripped INTEGER NOT NULL,
                latency_sec REAL NOT NULL,
                tier TEXT NOT NULL
            )
        """)
        con.close()
        logger.info("[TELEMETRY] DuckDB metrics database initialized at %s", _DB_PATH)
    except Exception as e:
        logger.warning(f"[TELEMETRY] Failed to initialize metrics DB: {e}")

def _record_compaction_metrics(metrics: dict, latency: float, tier: str):
    """Persist one compaction telemetry row. Non-blocking — failures are logged, not raised."""
    try:
        con = duckdb.connect(_DB_PATH)
        con.execute(
            """
            INSERT INTO compaction_log (id, timestamp, raw_tokens, compact_tokens, tokens_saved,
                                        savings_pct, messages_dropped, prefixes_stripped, latency_sec, tier)
            VALUES (nextval('compaction_log_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                time.strftime("%Y-%m-%dT%H:%M:%S"),
                metrics.get("raw_tokens", 0),
                metrics.get("compact_tokens", 0),
                metrics.get("tokens_saved", 0),
                metrics.get("savings_pct", 0.0),
                metrics.get("messages_dropped", 0),
                metrics.get("prefixes_stripped", 0),
                round(latency, 4),
                tier,
            ],
        )
        con.close()
    except Exception as e:
        logger.warning(f"[TELEMETRY] Failed to record metrics: {e}")

_init_metrics_db()


# --- STARTUP: Launch background health pings ---
@app.on_event("startup")
async def startup_event():
    # Start the async background health checker
    asyncio.create_task(health_ping_loop())
    logger.info("Background health monitor started.")


@app.on_event("shutdown")
async def shutdown_event():
    pass
    logger.info("Graceful shutdown complete.")


# --- PREMIUM DASHBOARD & WEB CHAT CLIENT ---
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request):
    from src.config import GROQ_API_KEYS, OPENROUTER_API_KEYS, NVIDIA_API_KEYS

    # Fetch initial stats
    success_rate = 0
    if stats.total_requests > 0:
        success_rate = round((stats.successful / stats.total_requests) * 100, 1)

    # Determine default active tab based on path
    default_tab = "dashboard" if request.url.path.endswith("/dashboard") else "chat"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hybrid AI Router | Console</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <!-- Markdown & Syntax Highlighting -->
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
        <style>
            :root {{
                --bg: #0a0e1a;
                --surface: #111827;
                --card: #1e293b;
                --border: rgba(255,255,255,0.08);
                --primary: #38bdf8;
                --accent: #818cf8;
                --success: #4ade80;
                --danger: #f87171;
                --warn: #fbbf24;
                --text: #f1f5f9;
                --text-muted: #94a3b8;
            }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: var(--bg);
                color: var(--text);
                font-family: 'Inter', -apple-system, sans-serif;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 1.5rem;
            }}
            .dashboard {{
                width: 100%;
                max-width: 720px;
            }}
            .header {{
                text-align: center;
                margin-bottom: 1.5rem;
            }}
            .status-pill {{
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                padding: 0.4rem 1rem;
                background: rgba(34, 197, 94, 0.15);
                color: var(--success);
                border-radius: 2rem;
                font-size: 0.8rem;
                font-weight: 600;
                letter-spacing: 0.05em;
                text-transform: uppercase;
                margin-bottom: 0.75rem;
            }}
            .status-pill .dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: var(--success);
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.4; }}
            }}
            h1 {{
                font-size: 2rem;
                font-weight: 700;
                background: linear-gradient(135deg, var(--primary), var(--accent));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 0.25rem;
            }}
            .subtitle {{
                color: var(--text-muted);
                font-size: 0.9rem;
            }}

            /* Tabs Navigation */
            .tabs-nav {{
                display: flex;
                background: rgba(255, 255, 255, 0.03);
                padding: 0.25rem;
                border-radius: 0.75rem;
                border: 1px solid var(--border);
                margin-bottom: 1.5rem;
                gap: 0.25rem;
            }}
            .tab-btn {{
                flex: 1;
                background: transparent;
                border: none;
                color: var(--text-muted);
                padding: 0.65rem 1rem;
                border-radius: 0.5rem;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.4rem;
            }}
            .tab-btn:hover {{
                color: var(--text);
                background: rgba(255, 255, 255, 0.02);
            }}
            .tab-btn.active {{
                color: var(--bg);
                background: var(--primary);
            }}

            /* Tab Panels */
            .tab-panel {{
                display: none;
            }}
            .tab-panel.active {{
                display: block;
            }}

            /* Stats Row */
            .stats-row {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 0.75rem;
                margin-bottom: 1.25rem;
            }}
            .stat-card {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 0.875rem;
                padding: 1rem;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .stat-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.3);
            }}
            .stat-val {{
                font-size: 1.5rem;
                font-weight: 700;
                color: var(--primary);
                line-height: 1;
                margin-bottom: 0.35rem;
            }}
            .stat-label {{
                font-size: 0.7rem;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}

            /* Section Header */
            .section-title {{
                font-size: 0.75rem;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.1em;
                margin-bottom: 0.6rem;
                padding-left: 0.25rem;
            }}

            /* Provider Grid */
            .provider-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 0.75rem;
                margin-bottom: 1.25rem;
            }}
            .provider-card {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 0.875rem;
                padding: 1rem;
                transition: transform 0.2s;
            }}
            .provider-card:hover {{
                transform: translateY(-2px);
            }}
            .provider-header {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-bottom: 0.5rem;
            }}
            .provider-icon {{ font-size: 1rem; }}
            .provider-name {{
                font-weight: 600;
                font-size: 0.9rem;
            }}
            .provider-status {{
                display: inline-block;
                padding: 0.2rem 0.6rem;
                border-radius: 1rem;
                font-size: 0.75rem;
                font-weight: 600;
            }}
            .provider-ago {{
                font-size: 0.7rem;
                color: var(--text-muted);
                margin-top: 0.4rem;
            }}

            /* Key Pool */
            .key-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 0.75rem;
                margin-bottom: 1.5rem;
            }}
            .key-card {{
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 0.875rem;
                padding: 1rem;
                text-align: center;
            }}
            .key-val {{
                font-size: 1.35rem;
                font-weight: 700;
                color: var(--accent);
            }}
            .key-label {{
                font-size: 0.7rem;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.05em;
                margin-top: 0.2rem;
            }}

            /* ==========================================
               CHAT CONSOLE STYLES
               ========================================== */
            .chat-box {{
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 1rem;
                display: flex;
                flex-direction: column;
                height: 480px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }}
            .chat-messages {{
                flex: 1;
                overflow-y: auto;
                padding: 1.25rem;
                display: flex;
                flex-direction: column;
                gap: 0.85rem;
                background: rgba(0,0,0,0.15);
            }}
            .msg {{
                display: flex;
                flex-direction: column;
                max-width: 85%;
                animation: fadeInMessage 0.25s ease-out forwards;
            }}
            @keyframes fadeInMessage {{
                from {{ opacity: 0; transform: translateY(5px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            .msg.user {{
                align-self: flex-end;
                align-items: flex-end;
            }}
            .msg.assistant {{
                align-self: flex-start;
                align-items: flex-start;
            }}
            .bubble {{
                padding: 0.75rem 1rem;
                border-radius: 0.875rem;
                font-size: 0.9rem;
                line-height: 1.45;
                word-break: break-word;
                white-space: pre-wrap;
            }}
            .msg.user .bubble {{
                background: var(--primary);
                color: #042f2e;
                font-weight: 500;
                border-bottom-right-radius: 0.25rem;
            }}
            .msg.assistant .bubble {{
                background: var(--card);
                color: var(--text);
                border-bottom-left-radius: 0.25rem;
                border: 1px solid var(--border);
            }}
            
            /* Markdown Styles */
            .bubble p {{ margin-bottom: 0.75rem; }}
            .bubble p:last-child {{ margin-bottom: 0; }}
            .bubble pre {{
                background: #0d1117;
                padding: 1rem;
                border-radius: 0.5rem;
                overflow-x: auto;
                margin: 0.75rem 0;
                border: 1px solid var(--border);
            }}
            .bubble code {{
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 0.85rem;
                background: rgba(0,0,0,0.3);
                padding: 0.15rem 0.3rem;
                border-radius: 0.25rem;
            }}
            .bubble pre code {{
                background: transparent;
                padding: 0;
            }}
            .bubble ul, .bubble ol {{
                margin-left: 1.5rem;
                margin-bottom: 0.75rem;
            }}
            .msg-meta {{
                font-size: 0.65rem;
                color: var(--text-muted);
                margin-top: 0.25rem;
                padding: 0 0.2rem;
            }}
            .input-area {{
                display: flex;
                padding: 0.75rem;
                background: var(--card);
                border-top: 1px solid var(--border);
                gap: 0.5rem;
            }}
            .chat-input {{
                flex: 1;
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 0.6rem;
                color: var(--text);
                padding: 0.65rem 0.85rem;
                font-family: inherit;
                font-size: 0.9rem;
                outline: none;
                resize: none;
                height: 42px;
                line-height: 1.3;
            }}
            .chat-input:focus {{
                border-color: var(--primary);
            }}
            .send-btn {{
                background: var(--primary);
                color: var(--bg);
                border: none;
                border-radius: 0.6rem;
                padding: 0 1.25rem;
                font-weight: 700;
                font-size: 0.85rem;
                cursor: pointer;
                transition: opacity 0.2s, background 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .send-btn:hover {{
                opacity: 0.9;
            }}
            .send-btn:disabled {{
                background: var(--card);
                color: var(--text-muted);
                cursor: not-allowed;
            }}
            .clear-btn {{
                background: transparent;
                color: var(--text-muted);
                border: 1px solid var(--border);
                border-radius: 0.6rem;
                padding: 0 1rem;
                font-weight: 600;
                font-size: 0.85rem;
                cursor: pointer;
                transition: all 0.2s;
            }}
            .clear-btn:hover {{
                background: rgba(255, 100, 100, 0.1);
                color: var(--danger);
                border-color: rgba(255, 100, 100, 0.3);
            }}

            /* Typist Indicator */
            .typing-indicator {{
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 0.5rem 0.85rem;
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 0.875rem;
                align-self: flex-start;
                margin-bottom: 0.5rem;
            }}
            .typing-indicator span {{
                width: 6px;
                height: 6px;
                background-color: var(--primary);
                border-radius: 50%;
                display: inline-block;
                animation: bounce 1.4s infinite ease-in-out both;
            }}
            .typing-indicator span:nth-child(1) {{ animation-delay: -0.32s; }}
            .typing-indicator span:nth-child(2) {{ animation-delay: -0.16s; }}
            @keyframes bounce {{
                0%, 80%, 100% {{ transform: scale(0); }}
                40% {{ transform: scale(1.0); }}
            }}

            footer {{
                text-align: center;
                color: var(--text-muted);
                font-size: 0.75rem;
                opacity: 0.6;
                margin-top: 1.5rem;
            }}

            /* Auto-refresh animation */
            .refresh-bar {{
                height: 2px;
                background: linear-gradient(90deg, transparent, var(--primary), transparent);
                border-radius: 1px;
                margin-bottom: 1.5rem;
                animation: sweep 30s linear infinite;
            }}
            @keyframes sweep {{
                0% {{ background-position: -200% center; }}
                100% {{ background-position: 200% center; }}
            }}
        </style>
    </head>
    <body>
        <div class="dashboard">
            <div class="header">
                <div class="status-pill"><span class="dot"></span> System Active</div>
                <h1>Hybrid AI Router</h1>
                <p class="subtitle">10-Tier SRE Routing Engine</p>
            </div>

            <!-- Tabs Navigation -->
            <div class="tabs-nav">
                <button id="btn-chat" class="tab-btn {'active' if default_tab == 'chat' else ''}" onclick="switchTab('chat')">💬 Chat Console</button>
                <button id="btn-dashboard" class="tab-btn {'active' if default_tab == 'dashboard' else ''}" onclick="switchTab('dashboard')">📊 SRE Dashboard</button>
            </div>

            <!-- ==========================================
                 TAB 1: CHAT PANEL
                 ========================================== -->
            <div id="panel-chat" class="tab-panel {'active' if default_tab == 'chat' else ''}">
                <div class="chat-box">
                    <div id="chat-messages" class="chat-messages">
                        <div class="msg assistant">
                            <div class="bubble">Welcome! I am your offsite Hybrid AI Router. How can I help you today?</div>
                            <div class="msg-meta">served by: system</div>
                        </div>
                    </div>
                    <div id="typing-container"></div>
                    <div class="input-area">
                        <button class="clear-btn" onclick="clearChat()" title="Clear Chat History">🗑️</button>
                        <textarea id="chat-input" class="chat-input" placeholder="Type your message... (Enter to send)" onkeydown="handleEnter(event)"></textarea>
                        <button id="send-btn" class="send-btn" onclick="sendMessage()">Send</button>
                    </div>
                </div>
            </div>

            <!-- ==========================================
                 TAB 2: DASHBOARD PANEL
                 ========================================== -->
            <div id="panel-dashboard" class="tab-panel {'active' if default_tab == 'dashboard' else ''}">
                <div class="refresh-bar"></div>

                <div class="section-title">Request Statistics</div>
                <div class="stats-row">
                    <div class="stat-card">
                        <div id="metric-total-requests" class="stat-val">{stats.total_requests}</div>
                        <div class="stat-label">Total Requests</div>
                    </div>
                    <div class="stat-card">
                        <div id="metric-success-rate" class="stat-val">{success_rate}%</div>
                        <div class="stat-label">Success Rate</div>
                    </div>
                    <div class="stat-card">
                        <div id="metric-last-latency" class="stat-val">{stats.last_latency:.1f}s</div>
                        <div class="stat-label">Last Latency</div>
                    </div>
                </div>

                <div class="section-title">Compaction & Telemetry</div>
                <div class="stats-row">
                    <div class="stat-card">
                        <div id="metric-tokens-saved" class="stat-val">Loading...</div>
                        <div class="stat-label">Tokens Saved</div>
                    </div>
                    <div class="stat-card">
                        <div id="metric-compaction-ratio" class="stat-val">Loading...</div>
                        <div class="stat-label">Compaction Ratio</div>
                    </div>
                    <div class="stat-card">
                        <div id="metric-active-tier" class="stat-val" style="color: var(--accent);">Loading...</div>
                        <div class="stat-label">Active Tier</div>
                    </div>
                </div>

                <div class="section-title">Provider Health</div>
                <div id="provider-grid" class="provider-grid">
                    <!-- Loaded dynamically via JS polling -->
                    <div class="provider-card" style="text-align: center; grid-column: span 2;">
                        <span class="provider-name">Initializing telemetry data...</span>
                    </div>
                </div>

                <div class="section-title">Key Pool</div>
                <div class="key-grid">
                    <div class="key-card">
                        <div class="key-val">{len(GROQ_API_KEYS)}</div>
                        <div class="key-label">Groq Keys</div>
                    </div>
                    <div class="key-card">
                        <div class="key-val">{len(OPENROUTER_API_KEYS)}</div>
                        <div class="key-label">OpenRouter Keys</div>
                    </div>
                    <div class="key-card">
                        <div class="key-val">{len(NVIDIA_API_KEYS)}</div>
                        <div class="key-label">NVIDIA Keys</div>
                    </div>
                </div>
            </div>

            <footer>End-to-End Resilience &bull; Private Space</footer>
        </div>

        <script>
            // Configure marked with highlight.js
            marked.setOptions({{
                highlight: function(code, lang) {{
                    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
                    return hljs.highlight(code, {{ language }}).value;
                }}
            }});

            // Chat history tracking
            let chatHistory = [];
            const savedHistory = localStorage.getItem("chatHistory");
            if (savedHistory) {{
                try {{
                    chatHistory = JSON.parse(savedHistory);
                }} catch (e) {{
                    chatHistory = [];
                }}
            }}

            if (chatHistory.length === 0) {{
                chatHistory = [
                    {{ role: "assistant", content: "Welcome! I am your offsite Hybrid AI Router. How can I help you today?" }}
                ];
                saveHistory();
            }}

            function saveHistory() {{
                localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
            }}

            // Render existing history on load
            window.onload = () => {{
                chatHistory.forEach(msg => {{
                    const meta = msg.role === "user" ? "you" : (msg.meta || "system");
                    renderMessage(msg.role, msg.content, meta, false);
                }});
            }};

            let isSending = false;

            // Tab switcher
            function switchTab(tabId) {{
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
                
                document.getElementById('btn-' + tabId).classList.add('active');
                document.getElementById('panel-' + tabId).classList.add('active');

                // If switching to dashboard, update metrics immediately
                if (tabId === 'dashboard') {{
                    fetchTelemetry();
                }}
            }}

            function handleEnter(e) {{
                if (e.key === 'Enter' && !e.shiftKey) {{
                    e.preventDefault();
                    sendMessage();
                }}
            }}

            async function sendMessage() {{
                const inputEl = document.getElementById('chat-input');
                const text = inputEl.value.trim();
                if (!text || isSending) return;

                isSending = true;
                inputEl.value = '';
                document.getElementById('send-btn').disabled = true;

                // 1. Render User Message
                renderMessage("user", text, "you", true);
                chatHistory.push({{ role: "user", content: text, meta: "you" }});
                saveHistory();

                // 2. Render Typing Indicator
                showTypingIndicator();

                try {{
                    // Post to local chat completions endpoint
                    const response = await fetch('/v1/chat/completions', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            model: "hybrid-router",
                            messages: chatHistory
                        }})
                    }});

                    hideTypingIndicator();

                    if (response.ok) {{
                        const data = await response.json();
                        const content = data.choices[0].message.content;
                        
                        // Parse out model tag if it exists in the response
                        let displayContent = content;
                        let providerName = data.model || "Router Cascade";

                        // Remove tag prefix if we show it in meta instead
                        if (content.startsWith('[🌊 Cascade]')) {{
                            displayContent = content.substring(12).trim();
                            providerName = "Waterfall Cascade";
                        }} else if (content.startsWith('[⚠️ Error]')) {{
                            displayContent = content.substring(10).trim();
                            providerName = "Cascade System Error";
                        }}

                        renderMessage("assistant", displayContent, providerName, true);
                        chatHistory.push({{ role: "assistant", content: content, meta: providerName }});
                        saveHistory();
                    }} else {{
                        const errData = await response.json();
                        renderMessage("assistant", "Error: " + (errData.error || "Failed to process completion request."), "system error");
                    }}
                }} catch (err) {{
                    hideTypingIndicator();
                    renderMessage("assistant", "Connection Error: Failed to contact the router endpoint.", "connection failure");
                    console.error(err);
                }} finally {{
                    isSending = false;
                    document.getElementById('send-btn').disabled = false;
                    inputEl.focus();
                }}
            }}

            function renderMessage(role, text, meta, animate = true) {{
                const msgsContainer = document.getElementById('chat-messages');
                const msgDiv = document.createElement('div');
                msgDiv.className = `msg ${{role}}`;
                if (!animate) msgDiv.style.animation = "none";
                
                let renderedText = text;
                if (role === "assistant") {{
                    // Parse markdown and sanitize
                    const rawHtml = marked.parse(text);
                    renderedText = DOMPurify.sanitize(rawHtml);
                }} else {{
                    renderedText = escapeHtml(text);
                }}

                msgDiv.innerHTML = `
                    <div class="bubble">${{renderedText}}</div>
                    <div class="msg-meta">served by: ${{escapeHtml(meta)}}</div>
                `;
                msgsContainer.appendChild(msgDiv);
                msgsContainer.scrollTop = msgsContainer.scrollHeight;
            }}

            function clearChat() {{
                if (confirm("Are you sure you want to clear the chat history?")) {{
                    localStorage.removeItem("chatHistory");
                    location.reload();
                }}
            }}

            function showTypingIndicator() {{
                const container = document.getElementById('typing-container');
                container.innerHTML = `
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                `;
                const msgsContainer = document.getElementById('chat-messages');
                msgsContainer.scrollTop = msgsContainer.scrollHeight;
            }}

            function hideTypingIndicator() {{
                document.getElementById('typing-container').innerHTML = '';
            }}

            function escapeHtml(text) {{
                const map = {{
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                }};
                return text.replace(/[&<>"']/g, function(m) {{ return map[m]; }});
            }}

            // AJAX Telemetry Fetching (SPA style)
            async function fetchTelemetry() {{
                try {{
                    // Fetch Compaction & General Stats
                    const effResponse = await fetch('/api/v1/metrics/efficiency', {{
                        headers: {{ 'Accept': 'application/json' }}
                    }});
                    if (effResponse.ok) {{
                        const data = await effResponse.json();
                        const summary = data.summary;
                        const recent = data.recent;

                        document.getElementById('metric-total-requests').innerText = summary.total_requests || 0;
                        
                        let successRate = 0;
                        if (summary.total_requests > 0) {{
                            successRate = ((summary.successful_requests / summary.total_requests) * 100).toFixed(1);
                        }}
                        document.getElementById('metric-success-rate').innerText = successRate + '%';
                        document.getElementById('metric-last-latency').innerText = (summary.avg_latency || 0).toFixed(1) + 's';

                        document.getElementById('metric-tokens-saved').innerText = Number(summary.total_tokens_saved || 0).toLocaleString();
                        document.getElementById('metric-compaction-ratio').innerText = (summary.avg_savings_pct || 0.0).toFixed(1) + '%';
                        
                        if (recent && recent.length > 0) {{
                            document.getElementById('metric-active-tier').innerText = recent[0].tier;
                        }} else {{
                            document.getElementById('metric-active-tier').innerText = 'N/A';
                        }}
                    }}

                    // Fetch Provider Statuses
                    const provResponse = await fetch('/health/providers');
                    if (provResponse.ok) {{
                        const providers = await provResponse.json();
                        let gridHtml = '';
                        
                        for (const key in providers) {{
                            const ps = providers[key];
                            let badgeBg = 'rgba(234, 179, 8, 0.2)';
                            let badgeColor = '#fbbf24';
                            let icon = '&#x23F3;';
                            let statusText = 'Checking...';

                            if (ps.status === 'up') {{
                                badgeBg = 'rgba(34, 197, 94, 0.2)';
                                badgeColor = '#4ade80';
                                icon = '&#x2705;';
                                statusText = ps.latency_ms + 'ms';
                            }} else if (ps.status === 'down') {{
                                badgeBg = 'rgba(239, 68, 68, 0.2)';
                                badgeColor = '#f87171';
                                icon = '&#x274C;';
                                statusText = ps.error || 'Down';
                            }}

                            let ago = '';
                            if (ps.last_checked > 0) {{
                                const secs = Math.floor(Date.now() / 1000 - ps.last_checked);
                                ago = secs < 60 ? secs + 's ago' : Math.floor(secs / 60) + 'm ago';
                            }}

                            gridHtml += `
                                <div class="provider-card">
                                    <div class="provider-header">
                                        <span class="provider-icon">${{icon}}</span>
                                        <span class="provider-name">${{ps.name}}</span>
                                    </div>
                                    <div class="provider-status" style="background:${{badgeBg}}; color:${{badgeColor}};">${{statusText}}</div>
                                    <div class="provider-ago">${{ago}}</div>
                                </div>
                            `;
                        }}
                        document.getElementById('provider-grid').innerHTML = gridHtml || '<div class="provider-card" style="text-align: center; grid-column: span 2;"><span class="provider-name">No providers monitored.</span></div>';
                    }}
                }} catch (err) {{
                    console.error('Error fetching telemetry data:', err);
                }}
            }}

            // Poll every 10 seconds for live updates
            setInterval(() => {{
                // Only poll if dashboard panel is currently visible to save resources
                if (document.getElementById('panel-dashboard').classList.contains('active')) {{
                    fetchTelemetry();
                }}
            }}, 10000);

            // Run initial load
            if (document.getElementById('panel-dashboard').classList.contains('active')) {{
                fetchTelemetry();
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = None

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if not request.messages:
        return JSONResponse(status_code=400, content={"error": "No messages provided"})
        
    last_msg = request.messages[-1]
    prompt_text = ""
    image_data = None

    # Handle standard text or multimodal payload
    if isinstance(last_msg.content, str):
        prompt_text = last_msg.content
    elif isinstance(last_msg.content, list):
        for part in last_msg.content:
            if part.get("type") == "text":
                prompt_text += part.get("text", "")
            elif part.get("type") == "image_url":
                # Expecting base64 image data in OpenAI format
                image_url = part.get("image_url", {}).get("url", "")
                if "base64," in image_url:
                    image_data = image_url.split("base64,")[1]
                else:
                    image_data = image_url # Assume raw base64 or URL

    # Validate Input Schema
    if not prompt_text and not image_data:
        return JSONResponse(status_code=422, content={"error": "Malformed request: No text or image found in last message."})

    # Serialize messages to plain dicts for downstream consumption
    messages_plain = []
    for msg in request.messages:
        if isinstance(msg.content, str):
            messages_plain.append({"role": msg.role, "content": msg.content})
        else:
            # Multimodal: flatten to text-only for the cascade (images handled separately)
            text_parts = "".join(p.get("text", "") for p in msg.content if p.get("type") == "text")
            messages_plain.append({"role": msg.role, "content": text_parts})

    # Send through our router
    start_time = time.time()
    try:
        response_text, model_label, compaction_metrics = classify_and_route(prompt_text, image_data=image_data, messages=messages_plain)
        elapsed = time.time() - start_time

        # Track stats
        stats.total_requests += 1
        stats.successful += 1
        stats.last_provider = model_label
        stats.last_latency = elapsed

        # Persist compaction telemetry to DuckDB
        _record_compaction_metrics(compaction_metrics, elapsed, model_label)
    except Exception as e:
        stats.total_requests += 1
        stats.failed += 1
        logger.error(f"Routing logic failure: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal System Error in routing logic."})
    
    # Tag the response so the user knows the source
    if "ERROR" in model_label:
        tag = "[⚠️ Error]"
    else:
        tag = "[🌊 Cascade]"
        
    formatted_response = f"{tag} {response_text}"
    
    # Format as an OpenAI-compatible JSON response
    response_json = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "hybrid-router",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": formatted_response,
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": compaction_metrics.get("compact_tokens", 0),
            "completion_tokens": 0,
            "total_tokens": compaction_metrics.get("compact_tokens", 0)
        }
    }
    
    logger.info(f"API Request completed in {elapsed:.1f}s -> {tag}")
    return response_json

@app.get("/v1/models")
async def get_models():
    return {
        "object": "list",
        "data": [{"id": "hybrid-router", "object": "model", "created": int(time.time()), "owned_by": "antigravity"}]
    }

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "3.0.0", "mode": "offsite"}

@app.get("/health/providers")
async def health_providers():
    """Detailed provider health status for programmatic consumption."""
    result = {}
    for pid, ps in provider_statuses.items():
        result[pid] = {
            "name": ps.name,
            "status": ps.status,
            "latency_ms": ps.latency_ms,
            "last_checked": ps.last_checked,
            "error": ps.error,
        }
    return result

@app.get("/health/circuits")
async def health_circuits():
    """Circuit breaker state for all tiers."""
    return get_circuit_status()



@app.get("/api/v1/metrics/efficiency")
def get_efficiency_metrics(request: Request):
    """Compaction telemetry — aggregate stats and last 10 records from DuckDB."""
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/dashboard")
    try:
        con = duckdb.connect(_DB_PATH, read_only=True)

        summary = con.execute("""
            SELECT
                COUNT(*)            AS total_requests,
                COALESCE(SUM(tokens_saved), 0)    AS total_tokens_saved,
                COALESCE(ROUND(AVG(savings_pct), 2), 0) AS avg_savings_pct,
                COALESCE(ROUND(AVG(latency_sec), 4), 0) AS avg_latency_sec,
                COALESCE(SUM(messages_dropped), 0) AS total_messages_dropped,
                COALESCE(SUM(prefixes_stripped), 0) AS total_prefixes_stripped
            FROM compaction_log
        """).fetchone()

        recent = con.execute("""
            SELECT timestamp, raw_tokens, compact_tokens, tokens_saved,
                   savings_pct, messages_dropped, prefixes_stripped, latency_sec, tier
            FROM compaction_log
            ORDER BY id DESC
            LIMIT 10
        """).fetchall()

        con.close()

        recent_records = [
            {
                "timestamp": r[0], "raw_tokens": r[1], "compact_tokens": r[2],
                "tokens_saved": r[3], "savings_pct": r[4], "messages_dropped": r[5],
                "prefixes_stripped": r[6], "latency_sec": r[7], "tier": r[8],
            }
            for r in recent
        ]

        return {
            "summary": {
                "total_requests": summary[0],
                "total_tokens_saved": summary[1],
                "avg_savings_pct": summary[2],
                "avg_latency_sec": summary[3],
                "total_messages_dropped": summary[4],
                "total_prefixes_stripped": summary[5],
            },
            "recent": recent_records,
        }
    except Exception as e:
        logger.error(f"[TELEMETRY] Metrics query failed: {e}")
        return JSONResponse(status_code=500, content={"error": f"Metrics unavailable: {e}"})