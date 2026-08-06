# Dostt Support Chatbot — Full System Documentation

## What It Is

The Dostt Support Chatbot is an AI-powered customer support assistant embedded inside the Dostt mobile app as a WebView. It helps two types of users resolve common issues, browse recent calls and transactions, and raise support tickets — all in their preferred language.

It is built as two separate services:

- **Backend** — Python FastAPI. Owns the conversation state machine, FAQ matching, ticket creation, and all calls to the Dostt API and Gemini AI.
- **Frontend** — React 18 + Vite. Renders the chat UI inside a WebView. Communicates with the native app via a bridge and with the backend via REST.

---

## User Types

| Type | Value sent in bridge | Who they are |
|---|---|---|
| USER | `USER` | Customers who buy coins and make calls |
| LISTENER | `LISTENER` | Experts/listeners who take calls and earn |

The user type is received from the native app via the WebView bridge on init. It controls which FAQs are shown, which API endpoints are called (calls vs. sessions, transactions vs. earnings/payouts), and how ticket references are categorized.

---

## Languages

11 languages supported:

`English`, `Hindi`, `Tamil`, `Telugu`, `Malayalam`, `Kannada`, `Marathi`, `Punjabi`, `Bengali`, `Gujarati`, `Odia`

All bot responses in non-English languages are written in **Roman script** (English alphabet) — not native script. The AI is instructed to follow this strictly.

The language is received from the native bridge on init and can also be changed mid-session via a language switch event.

---

## Architecture Overview

```
Native App (React Native)
        │
        │  WebView bridge (postMessage)
        │
   Frontend (React 18 / Vite)
   ├── useBridge.js       — receives INIT token/language/platform from native
   ├── useChat.js         — manages messages, isLoading, isTyping states
   ├── App.jsx            — wires bridge + chat + UI together
   ├── ChatContainer.jsx  — renders message list
   ├── Message.jsx        — renders each message type (text, cards, ticket)
   ├── MessageInput.jsx   — user text input
   └── analytics.js       — sends analytics events back to native via bridge
        │
        │  REST API (HTTP)
        │
   Backend (FastAPI)
   ├── routers/chat.py        — conversation state machine (all flow logic)
   ├── services/ai_service.py — Gemini calls (FAQ matching, response generation)
   ├── services/faq_service.py — FAQ loading, filtering, payout ID lookup
   ├── services/dostt_client.py — Dostt API calls (calls, transactions, tickets)
   ├── services/session_service.py — in-memory session store with TTL
   ├── services/translations.py — backend UI strings per language
   ├── services/faq_title_translations.py — production FAQ title translations
   ├── services/faq_title_translations_stag.py — staging FAQ title translations
   └── data/
       ├── faqs.json       — production FAQs
       └── faq-stag.json   — staging FAQs
```

---

## WebView Bridge

The chatbot runs inside a WebView, so it cannot access the native app directly. All communication goes through a string bridge.

### Native → WebView (on load)

The native app sends an `INIT` message once the WebView is ready:

```json
{
  "type": "INIT",
  "token": "<jwt>",
  "user_type": "USER",
  "language": "Hindi",
  "platform": "android",
  "app_version_code": "131"
}
```

### WebView → Native

The frontend sends messages to native using `window.ReactNativeWebView.postMessage`:

```json
{ "name": "webviewReady" }
{ "name": "analytics", "payload": { "name": "support_session_started", ... } }
```

---

## Session Lifecycle

1. Frontend receives `INIT` from bridge → token, language, user type available
2. Frontend calls `POST /api/session/init` with the token, language, user type, platform
3. Backend creates a session (UUID, stored in memory with 1-hour TTL), returns `session_id` + greeting + category cards
4. All subsequent messages use `POST /api/chat` with the `session_id`
5. Backend session expires after 1 hour of inactivity

---

## Conversation Flow

The conversation is driven by a state machine on the backend. Each session has a `stage` that determines how the next message is handled.

### Stage Map

```
AWAITING_CATEGORY_SELECTION
        │
        ├─── calls ──────────────────────► Fetch recent calls from Dostt API
        │                                         │
        │                                  AWAITING_CALL_SELECTION
        │                                         │ (user picks a call)
        │                                         │
        ├─── transactions                  ◄──────┘
        │       │                          │
        │       ├── USER ──────────────► Fetch recent transactions
        │       │                               │
        │       └── LISTENER                    │
        │               │              AWAITING_TRANSACTION_SELECTION
        │    AWAITING_TRANSACTION_SUBTYPE        │ (user picks a transaction)
        │       ├── earnings                     │
        │       │   └── Fetch earnings ─────────►│
        │       └── payouts                      │
        │           └── Fetch payouts ──────────►│
        │                                        │
        │                               AWAITING_FAQ_SELECTION
        │                                        │ (user picks an FAQ card)
        └─── other                               │
                │                                │
        AWAITING_OTHER_TEXT               ◄──────┘
                │ (user types free text)          │
                │ Gemini matches an FAQ ──────────┘
                │
                         [FAQ matched]
                                │
                         Gemini generates answer
                                │
                    ┌───────────┴──────────────┐
                    │                          │
             FEEDBACK_ONLY            RAISE_COMPLAINT or BOTH
                    │                          │
             _ask_more_help           ANSWERED stage
             (start again)                    │
                                      [Confirm ticket?]
                                              │
                                  AWAITING_TICKET_CONFIRMATION
                                              │
                                    [Confirm] [Edit] [Cancel]
                                              │
                                   AWAITING_CALL_CONSENT
                                    (opt-in for a callback call)
                                              │
                                    POST ticket to Dostt API
                                              │
                                       TICKET_CREATED
                                    (show ticket created card)
```

---

## The Three Categories

### 1. Calls

Shown to: USER and LISTENER

- **USER** → fetches recent calls from `/help-and-support/bookings/customers/`
- **LISTENER** → fetches recent sessions from `/help-and-support/bookings/experts/`

Only calls without an existing ticket are shown (filtered on `ticket_detail == null`). Up to 5 are shown. If none are available, the FAQ card list is shown directly.

User picks a call → FAQ cards for call-related issues appear → Gemini generates a response in context of the selected call.

---

### 2. Transactions

Shown to: USER and LISTENER

**USER:**
- Fetches coin transactions from `/help-and-support/payments/transactions`
- Only `Wallet Recharge` transactions without an existing ticket are shown

**LISTENER:**
- First asks: **Earnings** or **Payouts**?
- Earnings → fetches `/help-and-support/payments/earnings/`
- Payouts → fetches `/help-and-support/payments/payouts/`

User picks a transaction/earning/payout → FAQ cards appear → Gemini generates a response in context of the selected item.

---

### 3. Other

Shown to: USER and LISTENER

- User types a free-text message
- Gemini matches it against all FAQs visible to the user's type (confidence: HIGH / LOW / NONE)
- If HIGH/LOW match → answer is generated
- If no match on first try → bot asks to rephrase
- If no match on second try → bot apologises and shows "more help" options
- If the matched FAQ is a CALL or PAYMENT type → the bot transitions into that guided flow (call/transaction selection) before answering

---

## FAQ Feedback Types

Each FAQ has a `feedback_type` that controls what happens after the bot answers:

| Type | What happens after the answer |
|---|---|
| `FEEDBACK_ONLY` | Bot asks if this helped. No ticket option. |
| `RAISE_COMPLAINT_ONLY` | Ticket confirmation card shown immediately (no "do you need more help?" step) |
| `BOTH` | Bot answers, then asks "still facing this issue?" with Yes/No quick replies |

---

## Ticket Flow

1. User confirms they want to raise a ticket
2. **Ticket confirmation card** shown — displays: issue name, description, Confirm / Edit / Cancel
3. If Edit → user types new description → card re-shown with new text
4. If Confirm → **call consent** step: "Would you like a callback call?"
5. Ticket is submitted to Dostt API `POST /help-and-support/tickets/` with:
   - `issues` — FAQ ID
   - `description` — user's description
   - `type` — issue type (call / payment / other)
   - `reference_entity_id` — booking ID or transaction ID (if one was selected)
   - `reference_entity_type` — `"booking"` / `"dosttexpertpayout"` / `"transaction"`
   - `is_call_opted_in` — consent flag
   - `languages` — language code
6. On success → **Ticket created card** shown with the real `ticket_id` from the API
7. Max 2 tickets per session

---

## AI (Gemini)

Used for three things:

| Function | Model | What it does |
|---|---|---|
| `identify_faq` | gemini-3.5-flash | Structured JSON — which FAQ best matches the user's free text |
| `generate_*_response` | gemini-3.5-flash | Writes the conversational answer in simple language |
| `classify_ticket_intent` | gemini-3.5-flash | YES/NO — does the user's reply mean they want a ticket |

**Retry logic:** Primary model retried 3 times (1s / 2s / 2s delays) on 503 UNAVAILABLE. If all 3 fail, fallback model `gemini-3.5-flash-lite` is tried once.

**Language rules enforced via prompt:**
- Simple, childlike vocabulary
- Roman script only for non-English languages
- No markdown, no bold, plain text + numbered lists only
- Never mention FAQs, systems, or AI
- Never invent or change numbers/amounts from the FAQ

---

## Analytics Events

Three events are fired from the frontend and sent to the native app via the bridge:

```json
{ "name": "analytics", "payload": { "name": "support_session_started", "session_id": "...", "user_type": "USER", "language": "Hindi", "platform": "android" } }
{ "name": "analytics", "payload": { "name": "support_session_terminated", "session_id": "...", "reason": "restart" } }
{ "name": "analytics", "payload": { "name": "support_ticket_created", "session_id": "...", "ticket_id": 1234, "issue_name": "..." } }
```

The native app forwards these to Firebase / Mixpanel — no changes needed on the native side.

---

## Environment Configuration

A single flag `APP_ENV` in `.env` controls everything:

| | `staging` | `production` |
|---|---|---|
| Dostt API base URL | `testdostt.getlokalapp.com` | `api.dostt.in` |
| FAQ file | `faq-stag.json` (56 FAQs) | `faqs.json` (49 FAQs) |
| FAQ title translations | `faq_title_translations_stag.py` | `faq_title_translations.py` |
| Listener payout FAQ IDs | `{81}` | `{336, 337}` |

To switch to production: set `APP_ENV=production` in `.env` and restart the backend.

---

## Key Config Flags

| Flag | File | Default | Purpose |
|---|---|---|---|
| `APP_ENV` | `.env` | `production` | Switches between staging and production environments |
| `DUMMY_MODE` | `.env` | `false` | Returns hardcoded fake data instead of hitting the Dostt API |
| `GEMINI_MODEL` | `.env` / config | `gemini-3.5-flash` | Primary AI model |
| `GEMINI_FALLBACK_MODEL` | `.env` / config | `gemini-3.5-flash-lite` | Fallback AI model after 3 failed retries |
| `SESSION_TTL_SECONDS` | config | `3600` | Session expiry (1 hour) |

---

## File Reference

```
backend/
├── app/
│   ├── config.py                              — all settings, APP_ENV-driven properties
│   ├── main.py                                — FastAPI app entry point
│   ├── models/
│   │   ├── faq.py                             — FAQ, IssueType, FeedbackType, Visibility
│   │   ├── session.py                         — SessionState, ConversationStage, UserType
│   │   └── chat.py                            — request/response models
│   ├── routers/
│   │   └── chat.py                            — entire conversation state machine
│   └── services/
│       ├── ai_service.py                      — Gemini integration
│       ├── dostt_client.py                    — Dostt API calls + DUMMY_MODE
│       ├── faq_service.py                     — FAQ loading, filtering, get_faq_title dispatcher
│       ├── session_service.py                 — in-memory session store
│       ├── translations.py                    — UI strings in all 11 languages
│       ├── faq_title_translations.py          — production FAQ titles in Roman script
│       └── faq_title_translations_stag.py     — staging FAQ titles in Roman script
├── data/
│   ├── faqs.json                              — production FAQ data
│   └── faq-stag.json                          — staging FAQ data
└── .env                                       — GEMINI_API_KEY, APP_ENV

frontend/
└── src/
    ├── App.jsx                                — root component, wires all hooks
    ├── analytics.js                           — logEvent() + AnalyticsEvents constants
    ├── hooks/
    │   ├── useBridge.js                       — WebView ↔ native bridge
    │   └── useChat.js                         — session init, message sending, isTyping
    └── components/
        ├── ChatContainer.jsx                  — message list renderer
        ├── Message.jsx                        — individual message + card types
        └── MessageInput.jsx                   — text input + send button
```
