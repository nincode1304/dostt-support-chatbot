# Dostt Support Chatbot

AI-powered customer support chatbot for the Dostt mobile app, delivered as a mobile-first web page loaded in a WebView.

---

## Architecture

```
Mobile App WebView (?token=JWT&userType=USER)
        ↕
FastAPI backend  (Python, port 8000)
  ├─ serves compiled React SPA at /
  ├─ POST /api/session/init   → create session, get greeting
  ├─ POST /api/chat           → stateful conversation
  └─ GET  /api/health
        ↕ (internal)
  ├─ AI service (Claude Haiku)  — FAQ matching + natural response text
  ├─ FAQ service                — loads data/faqs.json, filters by user type
  ├─ Session service            — in-memory state machine with TTL
  └─ Dostt client               — calls Dostt API (real + stub endpoints)
```

**Key design principle:** The backend state machine drives all conversation flow decisions. Claude only generates natural language — it never decides which action to take, whether to raise a ticket, or which flow to follow.

---

## Conversation Flow

```
User sends message
  └─ AI identifies FAQ → No match → apologise + end
                       → Match found
                           └─ CALL issue   → fetch calls → show call cards → select
                           └─ PAYMENT issue → fetch txns  → show tx cards  → select
                           └─ OTHER issue  → answer directly
                                ↓ (based on FAQ response_action)
                           ANSWER_ONLY          → end
                           RAISE_TICKET         → show ticket confirmation
                           ANSWER_AND_RAISE_TICKET → answer + quick reply buttons
                                ↓
                           Ticket confirmation → confirm → create ticket → done
                                              → edit description → reconfirm
                                              → cancel → end
```

---

## Quick Start

### Prerequisites
- Python 3.11–3.13 (recommended; 3.14 requires `--pre` flag for pydantic)
- Node.js 18+
- An Anthropic API key

### 1. Backend

```bash
cd backend
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

# Python 3.11–3.13:
pip install -r requirements.txt

# Python 3.14 (if needed):
pip install --pre pydantic pydantic-settings && pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (development)

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 — proxies /api → :8000
```

### 3. Production build

```bash
cd frontend && npm run build   # outputs frontend/dist/
cd ../backend && uvicorn app.main:app --port 8000
# FastAPI now serves both the API and the compiled React SPA
```

---

## WebView Integration

Open this URL from the mobile app's WebView:

```
https://your-domain.com/?token=<JWT_TOKEN>&userType=USER
```

| Parameter | Values | Default |
|-----------|--------|---------|
| `token` | JWT bearer token | `null` (dev mode) |
| `userType` | `USER` \| `LISTENER` | `USER` |

Alternatively, after the WebView loads, call:

```javascript
window.postMessage(JSON.stringify({ type: "INIT", token: "JWT...", userType: "USER" }));
```

---

## TODO: Wire up missing API endpoints

Three endpoints in `backend/app/services/dostt_client.py` are stubs:

| Function | What to fill in |
|---|---|
| `get_recent_transactions()` | Replace `PAYMENT_TRANSACTIONS_ENDPOINT` with the real path |
| `get_recent_listener_sessions()` | Replace `LISTENER_SESSIONS_ENDPOINT` with the real path |
| `create_support_ticket()` | Replace `TICKET_CREATE_ENDPOINT` + verify request body fields |

Each stub has a docstring with the expected request/response shape. Update the URL and any payload fields, then remove the TODO comments.

---

## Adding or Editing FAQs

Edit `backend/data/faqs.json`. Each FAQ must have:

| Field | Values |
|---|---|
| `issue_id` | Unique string (e.g. `call_001`) |
| `visibility` | `USER` \| `LISTENER` \| `BOTH` |
| `issue_name` | Short display name |
| `question` | Example question |
| `answer` | Official business-approved answer (AI rewrites this conversationally) |
| `issue_type` | `CALL` \| `PAYMENT` \| `OTHER` |
| `response_action` | `ANSWER_ONLY` \| `RAISE_TICKET` \| `ANSWER_AND_RAISE_TICKET` |
| `keywords` | Array of matching keywords (improves AI matching accuracy) |

The app auto-reloads FAQs on startup. No code changes needed to add more FAQs.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key |
| `DOSTT_API_BASE_URL` | No | `https://testdostt.getlokalapp.com` | Dostt backend base URL |
| `CLAUDE_MODEL` | No | `claude-haiku-4-5-20251001` | Claude model to use |
| `SESSION_TTL_SECONDS` | No | `3600` | Session expiry (1 hour) |
| `MAX_RECENT_CALLS` | No | `5` | Max calls shown in call selector |
| `MAX_RECENT_TRANSACTIONS` | No | `5` | Max transactions shown |

---

## Project Structure

```
Chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entry point, static file serving
│   │   ├── config.py            Settings (env vars)
│   │   ├── models/
│   │   │   ├── faq.py           FAQ, Visibility, IssueType, ResponseAction
│   │   │   ├── session.py       SessionState, ConversationStage
│   │   │   └── chat.py          API request/response shapes
│   │   ├── services/
│   │   │   ├── ai_service.py    All Claude API calls
│   │   │   ├── faq_service.py   FAQ loading + filtering
│   │   │   ├── session_service.py Session CRUD + TTL cleanup
│   │   │   └── dostt_client.py  Dostt API client (real + stubs)
│   │   └── routers/
│   │       └── chat.py          Full conversation state machine
│   └── data/
│       └── faqs.json            49 support FAQs
└── frontend/
    └── src/
        ├── App.jsx              Root: wires bridge + chat hooks
        ├── hooks/
        │   ├── useChat.js       API calls, message list state
        │   └── useBridge.js     Reads auth from URL params or postMessage
        ├── components/
        │   ├── Header.jsx
        │   ├── ChatContainer.jsx
        │   ├── Message.jsx      Renders all message types
        │   ├── MessageInput.jsx
        │   ├── TypingIndicator.jsx
        │   ├── CallSelector.jsx
        │   ├── TransactionSelector.jsx
        │   ├── TicketConfirmation.jsx
        │   └── QuickReplies.jsx
        └── styles/globals.css   Mobile-first CSS with design tokens
```

---

## Extending for V2

| Feature | Where to add |
|---|---|
| Image/file attachments | `MessageInput.jsx` + new message type in `chat.py` |
| Human agent handoff | New `ConversationStage.ESCALATED` + webhook in `dostt_client.py` |
| Feedback collection | Post-conversation flow in `chat.py` after `ENDED` |
| Conversation analytics | Log to DB in `session_service.save_session()` |
| FAQ admin dashboard | Separate admin API + replace JSON file with a DB |
| Streaming responses | Replace `_call_claude()` with `stream=True` + SSE endpoint |
| Redis sessions | Replace `_sessions: dict` in `session_service.py` |
