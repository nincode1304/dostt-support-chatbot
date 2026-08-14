# Dostt Support Chatbot — Complete System Documentation

> This document explains the entire chatbot — what it is, how it works technically, how AI is used, how the flows work, how it connects to the app, and what edge cases it handles. Written to be understood by anyone on the team, not just engineers.

---

## Table of Contents

1. [The Vision](#1-the-vision)
2. [What It Is — In Simple Words](#2-what-it-is)
3. [Who Uses It](#3-who-uses-it)
4. [How It Fits Into the App](#4-how-it-fits-into-the-app)
5. [Technical Architecture](#5-technical-architecture)
6. [How the Frontend and Backend Talk to Each Other](#6-how-the-frontend-and-backend-talk-to-each-other)
7. [The WebView Bridge — How the App Passes Data In](#7-the-webview-bridge)
8. [Session Management](#8-session-management)
9. [The Conversation Flow](#9-the-conversation-flow)
10. [How AI (Gemini) Is Used](#10-how-ai-gemini-is-used)
11. [Content Safety Handling (Special Categories)](#11-content-safety-handling)
12. [The FAQ System](#12-the-faq-system)
13. [The Ticket Flow](#13-the-ticket-flow)
14. [Language Support](#14-language-support)
15. [Edge Cases and How They're Handled](#15-edge-cases-and-how-theyre-handled)
16. [Analytics](#16-analytics)
17. [Environment and Configuration](#17-environment-and-configuration)
18. [Dependencies](#18-dependencies)
19. [File Reference](#19-file-reference)

---

## 1. The Vision

The Dostt Support Chatbot was built to replace the traditional help-and-support experience (static FAQ pages, email forms, waiting for an agent) with something smarter and faster.

The goal: a user opens Help & Support, describes their problem in their own language, and the bot either gives them a clear answer immediately or raises a ticket on their behalf — without any human in the loop.

Key ideas behind the design:

- **Guided, not open-ended.** The bot walks the user through structured steps (pick a category, pick a call, pick an issue) so the conversation doesn't get lost. The user doesn't have to know what to type — they mostly tap cards.
- **AI only where it adds value.** Gemini is used to understand free-text messages and to write human answers in simple language. Everything else — routing logic, ticket creation, safety responses — is deterministic code. This keeps the bot predictable.
- **Multilingual from day one.** All 11 supported Indian languages work out of the box, with AI responses always in Roman script so they're readable on any device.
- **No promises the product can't keep.** The AI is explicitly told it cannot promise refunds, callbacks, timelines, or resolutions unless the FAQ literally states them.
- **Safety first.** Certain message types (mental health, abuse, minors, scams) get special treatment — predefined responses, no AI guessing, and in the case of an underage user, the chat is immediately closed.

---

## 2. What It Is

The Dostt Support Chatbot is a full-stack web application that runs inside the Dostt mobile app as a WebView (basically an in-app browser window). 

It consists of two parts:

| Part | Technology | What it does |
|---|---|---|
| **Frontend** | React 18 + Vite | The chat UI — text bubbles, card pickers, ticket form |
| **Backend** | Python + FastAPI | All the logic — state machine, AI calls, Dostt API calls, session storage |

The frontend is built into a static bundle (`npm run build`) and served directly by the FastAPI backend. So there is only one server to deploy.

When a user opens Help & Support in the Dostt app, the app opens a WebView pointing to this server. The chatbot loads, and a handshake happens between the app and the chatbot to pass in the user's identity (token, type, language).

---

## 3. Who Uses It

There are two types of users, and the bot behaves differently for each:

**USER** — someone who uses Dostt to make audio/video calls with Listeners. Their issues are about:
- Calls they made
- Coins they spent (wallet recharges)

**LISTENER** — someone who takes calls on Dostt and earns money. Their issues are about:
- Calls they received
- Earnings from those calls
- Payout requests (withdrawals)

The bot receives the user type from the app at startup and uses it to show only the relevant FAQs, fetch the right API data, and frame responses correctly.

---

## 4. How It Fits Into the App

The chatbot lives inside the Dostt mobile app via a **WebView** — an embedded browser view that the native app controls. This is a common pattern for shipping web-based features inside mobile apps without rebuilding them natively.

Here's the full journey:

```
User taps "Help & Support" in the Dostt app
            │
            ▼
Native app opens a WebView pointing to the chatbot URL
            │
            ▼
Chatbot page loads (React app)
            │
            ▼
Frontend sends "webviewReady" message to the native app
            │
            ▼
Native app replies with INIT: { token, user_type, language, platform, app_version_code }
            │
            ▼
Frontend calls POST /api/session/init with those values
            │
            ▼
Backend creates a session → returns greeting + category cards
            │
            ▼
User is now in the chatbot and the conversation begins
```

The native app doesn't need to know anything about the conversation. It just passes the user's identity in and receives analytics events back. Everything else is handled by the chatbot.

---

## 5. Technical Architecture

```
Dostt Mobile App (React Native)
│
│   WebView + postMessage bridge
│
├── Frontend  /  React 18 + Vite
│   │
│   ├── App.jsx                  Root component — wires bridge, chat, and UI
│   ├── hooks/useBridge.js       Receives INIT message from native app
│   ├── hooks/useChat.js         Manages all messages, loading state, session
│   ├── hooks/useViewportHeight  Handles keyboard height on Android WebView
│   ├── components/
│   │   ├── ChatContainer.jsx    Renders the scrollable message list
│   │   ├── Message.jsx          Renders each message type (text, cards, ticket forms)
│   │   └── MessageInput.jsx     Text input box + send button
│   ├── analytics.js             Fires events to native app via bridge
│   └── translations.js          UI string translations for the frontend (FE-side strings only)
│
│   HTTP REST API
│
└── Backend  /  Python + FastAPI
    │
    ├── main.py                  Server entry point. Also serves the React build.
    ├── config.py                All config (env vars, API URLs, model names)
    ├── routers/
    │   └── chat.py              The entire conversation state machine. All logic lives here.
    ├── models/
    │   ├── chat.py              Request/response shapes (Pydantic models)
    │   ├── session.py           Session state, stages, user type
    │   └── faq.py               FAQ model, IssueType, FeedbackType, Visibility
    └── services/
        ├── ai_service.py        All Gemini calls — intent detection, response generation
        ├── dostt_client.py      Dostt API calls (calls, transactions, tickets) + DUMMY_MODE
        ├── faq_service.py       FAQ loading from JSON, filtering by visibility + user type
        ├── session_service.py   In-memory session store with 1-hour TTL + cleanup loop
        ├── translations.py      All bot text in all 11 languages (backend-side strings)
        ├── faq_title_translations.py       FAQ card titles for production (Roman script)
        └── faq_title_translations_stag.py  FAQ card titles for staging

    data/
    ├── faqs.json        Production FAQ database
    └── faq-stag.json    Staging FAQ database
```

---

## 6. How the Frontend and Backend Talk to Each Other

The frontend talks to the backend via two REST API calls. That's it — just two endpoints.

### POST /api/session/init

Called once when the chatbot first loads. Sends the user's identity, gets back a `session_id` and the first messages.

**Request:**
```json
{
  "auth_token": "<jwt from native app>",
  "user_type": "USER",
  "language": "Hindi",
  "platform": "android",
  "app_version_code": "131"
}
```

**Response:**
```json
{
  "session_id": "abc123-...",
  "greeting": "Namaste! Main Dostt Support hun...",
  "items": [
    { "type": "text", "content": "Namaste!..." },
    { "type": "category_cards", "data": { ... } }
  ]
}
```

### POST /api/chat

Called for every subsequent user interaction — whether they typed something, tapped a card, confirmed a ticket, or anything else.

**Request:**
```json
{
  "session_id": "abc123-...",
  "type": "text",
  "message": "mera wallet recharge nahi hua",
  "selected_id": null
}
```

**Response:**
```json
{
  "session_id": "abc123-...",
  "items": [
    { "type": "text", "content": "Hum samajh sakte hain..." },
    { "type": "quick_replies", "data": { "options": [...] } }
  ]
}
```

The `items` array can contain multiple things at once — a text message followed by cards, or a text message followed by quick-reply buttons. The frontend renders them in order.

### Message Types the Backend Can Send

| Type | What it renders |
|---|---|
| `text` | A chat bubble with text |
| `category_cards` | The three main choice cards (Calls / Transactions / Other Issues) |
| `transaction_subtype_cards` | Earnings or Payouts? (Listener only) |
| `call_cards` | The user's recent calls as swipeable cards |
| `transaction_cards` | The user's recent transactions as swipeable cards |
| `faq_cards` | The list of FAQ options the user can pick from |
| `ticket_confirmation` | The confirm/edit/cancel ticket card |
| `ticket_created` | The success card with the ticket ID |
| `quick_replies` | Yes/No or other single-tap button choices |
| `chat_ended` | Disables the input and shows a close message |
| `error` | An error message |

### Message Types the Frontend Can Send

| Type | When it's sent |
|---|---|
| `text` | User typed and hit send |
| `select_category` | User tapped Calls, Transactions, or Other Issues |
| `select_transaction_subtype` | Listener chose Earnings or Payouts |
| `select_call` | User tapped a call card |
| `select_transaction` | User tapped a transaction card |
| `select_faq` | User tapped an FAQ card |
| `confirm_ticket` | User tapped Confirm on the ticket card |
| `edit_ticket` | User tapped Edit and typed a new description |
| `cancel` | User tapped Cancel |
| `consent_yes` / `consent_no` | User answered the callback consent question |
| `more_help_yes` / `more_help_no` | User answered the "anything else?" question |
| `set_language` | User switched language |

---

## 7. The WebView Bridge

Since the chatbot runs inside a WebView, it has no direct access to the native app's data (no token, no user info). The native app passes everything in via `postMessage` — the same mechanism browsers use for cross-frame communication.

### How the handshake works

**Step 1:** When the React app loads, it immediately sends `"webviewReady"` to native:
```js
window.ReactNativeWebView.postMessage(JSON.stringify({ name: "webviewReady" }))
```

**Step 2:** The native app receives this and responds with an `INIT` message:
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

**Step 3:** The frontend (`useBridge.js`) listens for this and stores the values. The INIT is only accepted once — any later attempts to re-send INIT are ignored (security measure to prevent token hijacking via the chat).

**Step 4:** The frontend calls `/api/session/init` with those values and the conversation starts.

**Note for developers:** When running the chatbot in a browser (not inside the native app), `window.ReactNativeWebView` doesn't exist. In that case, `useBridge.js` falls back to `{ token: "dev", userType: "USER", platform: "web" }` automatically, so you can test in a browser without the native app.

---

## 8. Session Management

Each conversation is a **session** stored in the backend's memory.

- Sessions are identified by a UUID (`session_id`) generated at init
- Each session stores: auth token, user type, language, current stage, selected call/transaction, matched FAQ, ticket count, message history, and timestamps
- Sessions expire after **1 hour of inactivity** (configurable via `SESSION_TTL_SECONDS`)
- A background cleanup task runs every 5 minutes and deletes expired sessions
- Sessions are stored in a Python dictionary in memory — there is no database. If the server restarts, all sessions are lost and users get a session error on their next message.

If a session is not found (expired or server restarted), the backend returns a 404 and the frontend shows a session error telling the user to reopen the chat from the app.

---

## 9. The Conversation Flow

The conversation is driven by a **state machine** on the backend. Every session has a `stage` (e.g. `AWAITING_CALL_SELECTION`, `AWAITING_FAQ_SELECTION`, etc.) and the backend uses it to decide how to handle the next incoming message.

### Stage lifecycle

```
AWAITING_CATEGORY_SELECTION (start/restart)
    │
    ├─ "calls"          → fetch calls → AWAITING_CALL_SELECTION
    │                                       │
    │                                   user picks → AWAITING_FAQ_SELECTION
    │                                                       │
    ├─ "transactions"   → (USER) fetch recharges            │
    │                    (LISTENER) AWAITING_TRANSACTION_SUBTYPE
    │                         ├─ earnings → fetch earnings  │
    │                         └─ payouts  → fetch payouts   │
    │                                   user picks → AWAITING_FAQ_SELECTION
    │                                                       │
    └─ "other"          → AWAITING_OTHER_TEXT               │
                               │                            │
                          user types → Gemini matches FAQ ──┘
                                                │
                                        Gemini generates answer
                                                │
                              ┌─────────────────┼─────────────────┐
                              │                 │                 │
                      FEEDBACK_ONLY        RAISE_COMPLAINT     BOTH
                          │                  │ (raise_ticket    │
                     more help            AWAITING_TICKET    ANSWERED
                                          CONFIRMATION       (ask if still
                                                │             facing it)
                                         confirm/edit/cancel
                                                │
                                     AWAITING_CALL_CONSENT
                                         (callback yes/no)
                                                │
                                          POST ticket to API
                                                │
                                         TICKET_CREATED
                                                │
                                         AWAITING_MORE_HELP_RESPONSE
                                                │
                                  ┌─────────────┴─────────────┐
                                  │                           │
                                 Yes                          No
                            (reset → AWAITING_CATEGORY)    ENDED
```

### The three main paths

**Path 1 — Calls**
1. Backend calls `GET /help-and-support/bookings/customers/` (USER) or `GET /help-and-support/bookings/experts/` (LISTENER)
2. Filters out calls that already have a ticket attached
3. Shows up to 5 call cards (date, name, duration, coins)
4. User picks one → FAQ cards appear → user picks an issue
5. Gemini generates an answer referencing the specific call

**Path 2 — Transactions**
1. If LISTENER: first ask "Earnings or Payouts?"
2. Fetch from the right endpoint:
   - USER → `GET /help-and-support/payments/transactions`
   - LISTENER earnings → `GET /help-and-support/payments/earnings/`
   - LISTENER payouts → `GET /help-and-support/payments/payouts/`
3. Shows up to 5 cards → user picks one → FAQ cards → Gemini answers

**Path 3 — Other Issues (free text)**
1. User types anything in any language or script
2. Backend first checks for mental health keywords (no AI, instant)
3. If not a mental health message → single Gemini call to classify the message
4. Gemini returns one of three outcomes:
   - `SPECIAL:<category>` → predefined response, no further routing
   - `FAQ:<id>` → answer from that FAQ (may redirect to Calls or Transactions path first)
   - `UNKNOWN` → route to the generic "other issues" FAQ (ID 397), which always raises a ticket

---

## 10. How AI (Gemini) Is Used

Gemini is used for **three specific purposes** only. Everything else is hardcoded logic.

### Purpose 1 — Intent detection and FAQ matching (`identify_other_intent`)

When the user types a free-text message in the "Other Issues" path, one Gemini call figures out:
- Is this a SPECIAL situation? (sensitive, off-topic, abusive, etc.)
- Or does it match one of the FAQs?

This is a single Gemini call that returns a one-line text response:
```
SPECIAL:MENTAL_HEALTH
FAQ:364
UNKNOWN
```

Gemini is given the full list of FAQ titles and the user's message. It decides which FAQ fits, or whether the message is a special case.

**For the SPECIAL check:** Gemini is given strict rules for 13 special categories. It must pick the right one based on the message content.

**For FAQ matching:** Gemini reads the FAQ titles and picks the best match. It also determines the FAQ type (CALL, PAYMENT, OTHER) so the bot knows whether to redirect to the calls/transactions flow first.

**For UNKNOWN:** If no FAQ matches and no special category applies, Gemini returns `UNKNOWN`. This routes to a generic "other issues" FAQ that always leads to a ticket.

### Purpose 2 — Generating the answer (`generate_initial_response`)

Once a FAQ is identified, Gemini writes the actual answer in conversational language. It receives:
- The FAQ's text (as factual bullet points to avoid paraphrasing issues)
- The user's original message
- The call or transaction the user selected (if any)
- The user type (USER or LISTENER)
- The language instruction

Gemini writes the response. The backend then decides what to do after the response (show ticket option, ask "still facing this?", or just move to "anything else?") based on the FAQ's `feedback_type` field — not Gemini.

### Purpose 3 — Identify FAQ (for FAQ cards path)

When the user picks a FAQ card directly from the list (not via free text), `identify_faq` is also called to confirm the match before generating the answer. This is a structured JSON response with a confidence level.

### AI guardrails built into the system prompt

The Gemini system prompt enforces:
- Simple, childlike vocabulary only
- Plain text — no bold, no markdown, no headers
- Roman script for non-English languages (no native script characters)
- Never mention FAQs, databases, or AI
- Never invent numbers, amounts, or conditions not in the FAQ
- **PROMISE RULES:** Never promise refunds, callbacks, timelines, or resolutions unless the FAQ explicitly states them

### Retry and fallback logic

- Primary model: `gemini-3.5-flash`
- If the primary returns a 503 (unavailable), it retries 3 times with delays of 1s, 2s, 2s
- After 3 failures, it tries once with the fallback: `gemini-3.5-flash-lite`
- If that also fails, it returns `null` and the backend falls back to the UNKNOWN path

---

## 11. Content Safety Handling

Certain messages skip FAQ matching entirely and get a predefined, pre-translated response. Gemini only does the routing decision — it does NOT write these responses. The responses are hardcoded strings in all 11 languages.

### 13 Special Categories

| Category | What triggers it | What the bot does |
|---|---|---|
| `MENTAL_HEALTH` | Mentions of suicide, self-harm, wanting to die | Gives Tele-MANAS helpline number. Stays in the chat — does not end it. |
| `ABUSE_SAFETY` | User says they are being abused, harassed, or threatened by any person (family, partner, colleague, stranger, etc.) | Gives an empathetic response + safety information. Stays in the chat. |
| `MINOR_USER` | User clearly states they themselves are under 18 | Explains Dostt is 18+ only. **Ends the chat immediately** — no FAQ, no ticket, no further messages. |
| `HARMFUL` | Explicit sexual content, graphic violence, threats to harm others | Redirects back to app issues |
| `VERBAL_ABUSE` | Profanity or insults directed at the bot/platform | Acknowledges frustration, asks for the actual issue |
| `PRIVACY_PROBING` | Asking for user data, passwords, or how to exploit the app | Declines politely |
| `PROMPT_INJECTION` | Trying to change the bot's identity or override its instructions | Declines and stays on task |
| `SPAM_GIBBERISH` | Random characters, keyboard mashing, completely unintelligible | Says it didn't understand and asks again |
| `OFF_TOPIC` | Completely unrelated to Dostt (politics, cricket, etc.) | Redirects to Dostt issues |
| `LEGAL_THREAT` | Explicitly threatening to sue or take formal legal action | Gives grievance officer email |
| `CALL_REQUEST` | User wants support to phone them back | Explains it can't arrange calls, offers a ticket instead |
| `SCAM_FRAUD` | Claims they were scammed or the platform is fraudulent | Will raise a ticket for the trust & safety team |
| `MISINFORMATION` | Claims to be Dostt staff, or spreading false platform information | Explains all official comms come through the app |

### MENTAL_HEALTH — extra handling

Mental health keywords are also checked **before** the Gemini call, as a safety net. There's a hardcoded list of keywords (suicide, self-harm, etc.) in the backend. If the message hits this check, the helpline response is sent immediately — no API call, no Gemini call. This is intentionally instant.

### MINOR_USER — special flow

When a user is identified as under 18:
1. Show the predefined underage message (in their language)
2. Immediately set the session stage to `ENDED`
3. Send a `chat_ended` response item — disabling the input box
4. No ticket, no FAQ, no "anything else?" — the conversation stops completely

**What counts as under 18 (for Gemini's classification):**
- Explicit self-stated age under 18: "I am 16", "I'm 17", "I'm 15 years old"
- Clear statements: "I'm a minor", "I'm underage", "I'm not 18 yet", "I am below 18"
- Equivalent phrases in any of the 11 supported languages

**What does NOT count:**
- Poor English or grammar
- Sounding young or using slang
- Saying "I'm in school" without an age
- Mentioning their parents or a younger sibling/friend who is under 18
- Any ambiguous statement that could apply to an adult

---

## 12. The FAQ System

FAQs are the backbone of the bot. Everything the bot knows about Dostt's policies comes from the FAQ database.

### FAQ data structure

Each FAQ has:
- `id` — unique integer
- `name` — internal name (for reference)
- `title11` — the question shown to users
- `answer` — the full HTML answer
- `answer_plain` — the HTML-stripped version (used by Gemini)
- `visibility` — who sees it: USER (0), LISTENER (1), or BOTH (2)
- `type` — what kind of issue it is: OTHER (0), CALL (1), PAYMENT (2), ALL (3)
- `feedback_type` — what happens after the answer:
  - `FEEDBACK_ONLY (1)` — answer only, no ticket
  - `RAISE_COMPLAINT_ONLY (2)` — go straight to ticket flow after the answer
  - `BOTH (3)` — answer first, then ask "still facing this issue?" and offer a ticket

FAQs are loaded from a JSON file at server startup (`faqs.json` for production, `faq-stag.json` for staging). HTML is stripped from `answer` to create `answer_plain` at load time.

### FAQ title translations

FAQ card titles are shown in the user's selected language. These translations live in two Python files:
- `faq_title_translations.py` — production FAQ titles
- `faq_title_translations_stag.py` — staging FAQ titles

These are separate from the general `translations.py` because FAQ titles change when the FAQ database changes.

### The generic "other issues" FAQ (ID 397)

If Gemini classifies a message as `UNKNOWN` (app-related, but no specific FAQ matches), the bot routes to FAQ 397. This FAQ's `feedback_type` is `RAISE_COMPLAINT_ONLY`, meaning the bot will always offer to raise a ticket. This ensures no user message goes unanswered — even if the specific issue isn't in the FAQ list, the user can still log a ticket.

---

## 13. The Ticket Flow

Tickets are the primary resolution mechanism. When a user has an unresolved issue, a ticket is created in Dostt's backend so the support team can follow up.

### How it works

**Step 1 — Decide to raise a ticket**

This depends on the FAQ's `feedback_type`:
- `RAISE_COMPLAINT_ONLY` → bot asks "Would you like to raise a support ticket for this issue?" immediately after the answer
- `BOTH` → bot asks "Are you still facing this issue?" If yes, proceed to ticket. If no, end gracefully.
- `FEEDBACK_ONLY` → no ticket option at all

**Step 2 — Ticket confirmation card**

User sees a card with:
- Issue name (the FAQ title)
- Description (the user's original typed message)
- Three buttons: **Confirm**, **Edit**, **Cancel**

If Edit: user types a new description → card is shown again with the new text.

**Step 3 — Callback consent**

When the user taps Confirm:
- "Would you like our team to call you directly to help resolve this?"
- If outside business hours (before 9 AM or after 7 PM IST), a note is shown saying callbacks happen during business hours

**Step 4 — Ticket submitted to Dostt API**

`POST /help-and-support/tickets/` with:
```json
{
  "issues": 364,
  "description": "user's message here",
  "type": 1,
  "reference_entity_id": 40549,
  "reference_entity_type": "booking",
  "is_call_opted_in": true,
  "languages": "Hindi"
}
```

On success: a ticket created card is shown with the ticket ID.

On failure: the API's error message is shown and the chat ends.

**Ticket limit:** Maximum 2 tickets per session. After 2, the ticket option is suppressed and the bot moves to "anything else?"

---

## 14. Language Support

The bot fully supports 11 Indian languages:

`English`, `Hindi`, `Tamil`, `Telugu`, `Malayalam`, `Kannada`, `Marathi`, `Punjabi`, `Bengali`, `Gujarati`, `Odia`

### How language works

There are two distinct layers of language handling:

**Layer 1 — Static UI strings (backend `translations.py` + frontend `translations.js`)**

Every UI message — greetings, prompts, buttons, error messages, content safety responses — is pre-written in all 11 languages. No AI is used for these. They're just looked up by key and language.

Example keys: `greeting`, `still_facing`, `raise_ticket_prompt`, `content_mental_health`, `content_minor_user`, etc.

**Layer 2 — AI-generated answers**

When Gemini writes an answer to a support question, it's given a language instruction like:
> "Write your ENTIRE response in Hindi using ONLY Roman script (English alphabet A–Z)."

Gemini writes in that language, in Roman script. It is never allowed to output native script characters (no Devanagari, no Tamil script, etc.) — this is enforced to ensure readability on older devices and to keep the UI consistent.

### Language switching

- Language defaults to **English** at session start or restart
- The user can switch language at any time using the language selector in the header
- When they switch, the `SET_LANGUAGE` message type is sent and all future responses come in the new language

---

## 15. Edge Cases and How They're Handled

| Situation | What happens |
|---|---|
| **Auth token invalid (401)** | Any API call returning 401 ends the session with an error message. User must reopen from the app. |
| **No recent calls/transactions** | Bot says "No recent activity found" and moves to "anything else?" |
| **All calls/transactions already have tickets** | Same as no activity — filtered list comes back empty |
| **Ticket limit reached (2 per session)** | Bot tells the user the limit is reached and moves on. No ticket option shown. |
| **Gemini API down** | 3 retries on primary model, then 1 attempt on lite fallback. If all fail, UNKNOWN flow handles it. |
| **Gemini returns unexpected output** | Response is treated as UNKNOWN and routed to FAQ 397 |
| **User restarts the chat** | All selected data is cleared (call, transaction, FAQ, description). Ticket count carries over (cannot raise more than 2 total). Stage resets to category selection. |
| **Session expired or server restarted** | Backend returns 404 for the session_id. Frontend shows error and tells user to reopen from the app. |
| **User is under 18** | Predefined response shown. Chat immediately ends. No further input accepted. |
| **User types in native script (e.g., Devanagari)** | Gemini understands it regardless. Bot still responds in Roman script for the selected language. |
| **User types in a language different from their selected bot language** | Gemini understands and still classifies correctly. The answer is always generated in the selected language. |
| **FAQ has no call/transaction needed** | If `type == OTHER`, Gemini answers directly without needing to pick a call or transaction first. |
| **Off-hours callback request** | The consent screen shows an additional note about business hours. The consent is still recorded and submitted with the ticket. |
| **UNKNOWN free-text (no FAQ match)** | Routes to FAQ 397 — a generic "other issues" FAQ that immediately proceeds to the ticket flow. |

---

## 16. Analytics

Three analytics events are fired from the frontend and sent back to the native app via the bridge:

| Event | When it fires |
|---|---|
| `support_session_started` | Session init successful — user has entered the chatbot |
| `support_session_terminated` | User taps restart or the session ends for any reason |
| `support_ticket_created` | A ticket is successfully submitted to the Dostt API |

The native app receives these via `window.ReactNativeWebView.postMessage` and forwards them to Firebase / Mixpanel. No changes needed on the native side to receive these events.

---

## 17. Environment and Configuration

A single `.env` file controls the entire system.

### Key flags

| Flag | Default | What it does |
|---|---|---|
| `GEMINI_API_KEY` | (required) | Google Gemini API key |
| `APP_ENV` | `production` | `staging` or `production` — controls API base URL and FAQ file |
| `DUMMY_MODE` | `false` | When `true`, returns hardcoded fake data instead of hitting the Dostt API. For local testing. |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Primary AI model |
| `GEMINI_FALLBACK_MODEL` | `gemini-3.5-flash-lite` | Fallback if primary fails 3 times |
| `SESSION_TTL_SECONDS` | `3600` | Session timeout in seconds (default: 1 hour) |
| `MAX_RECENT_CALLS` | `5` | Max call cards shown |
| `MAX_RECENT_TRANSACTIONS` | `5` | Max transaction cards shown |

### Staging vs Production

| | Staging | Production |
|---|---|---|
| Dostt API URL | `testdostt.getlokalapp.com` | `api.dostt.in` |
| FAQ file | `faq-stag.json` | `faqs.json` |
| FAQ titles | `faq_title_translations_stag.py` | `faq_title_translations.py` |
| Listener payout FAQ IDs | `{81}` | `{336, 337}` |

To switch: change `APP_ENV=staging` or `APP_ENV=production` in `.env` and restart the backend.

---

## 18. Dependencies

### Backend (Python)

| Package | What it's used for |
|---|---|
| `fastapi` | Web framework — defines all API routes |
| `uvicorn` | ASGI server — runs the FastAPI app |
| `pydantic` / `pydantic-settings` | Data validation and `.env` config loading |
| `google-genai` | Official Google Gemini SDK |
| `httpx` | Async HTTP client for Dostt API calls |
| `python-multipart` | Enables form data parsing (FastAPI dependency) |

### Frontend (Node / React)

| Package | What it's used for |
|---|---|
| `react` + `react-dom` | UI framework |
| `vite` | Build tool — bundles React into static files |
| `react-markdown` | Renders AI-generated text with markdown support |
| `remark-gfm` | GitHub-flavored markdown plugin for react-markdown |

### External Services

| Service | What it's used for |
|---|---|
| **Google Gemini** | AI: intent detection, FAQ matching, response generation |
| **Dostt API** | Fetching calls, transactions, earnings, payouts; submitting tickets |

---

## 19. File Reference

```
/
├── CHATBOT.md              ← This file
├── CONVERSATION_FLOW.md    ← Visual flow diagram + stage reference
├── flowchart.md            ← Full mermaid flowchart
├── API_REFERENCE.md        ← Dostt API endpoint reference
├── render.yaml             ← Deployment config (Render.com)

backend/
├── .env                    ← GEMINI_API_KEY, APP_ENV, DUMMY_MODE (not committed)
├── app/
│   ├── main.py             ← FastAPI entry point. Also serves React build.
│   ├── config.py           ← All settings and environment-driven properties
│   ├── models/
│   │   ├── chat.py         ← API request/response types (MessageInputType, ResponseItemType)
│   │   ├── session.py      ← SessionState, ConversationStage enum, UserType
│   │   └── faq.py          ← FAQ model, IssueType, FeedbackType, Visibility
│   ├── routers/
│   │   └── chat.py         ← The entire conversation state machine. All flow decisions live here.
│   └── services/
│       ├── ai_service.py                       ← All Gemini calls
│       ├── dostt_client.py                     ← Dostt API integration + DUMMY_MODE
│       ├── faq_service.py                      ← FAQ loading, filtering, title lookup
│       ├── session_service.py                  ← In-memory session store + TTL cleanup
│       ├── translations.py                     ← All bot text in all 11 languages
│       ├── faq_title_translations.py           ← Production FAQ titles in Roman script
│       └── faq_title_translations_stag.py      ← Staging FAQ titles in Roman script
├── data/
│   ├── faqs.json           ← Production FAQ database
│   └── faq-stag.json       ← Staging FAQ database

frontend/
└── src/
    ├── App.jsx             ← Root component — wires bridge + chat + UI
    ├── analytics.js        ← logEvent() and analytics event constants
    ├── translations.js     ← UI string translations on the frontend side
    ├── hooks/
    │   ├── useBridge.js            ← WebView ↔ native bridge (INIT + postMessage)
    │   ├── useChat.js              ← Session init, message sending, state management
    │   └── useViewportHeight.js    ← Keyboard-aware height on Android WebView
    └── components/
        ├── ChatContainer.jsx   ← Scrollable message list
        ├── Message.jsx         ← Renders each message type (text, cards, ticket forms)
        └── MessageInput.jsx    ← Text input + send button
```

---

## Quick Summary

| Question | Answer |
|---|---|
| What is it? | An in-app customer support chatbot running as a WebView |
| Where does it run? | Inside the Dostt app (Android/iOS) via WebView |
| How does the app pass user data in? | WebView bridge (postMessage INIT message) |
| What server does it run on? | One FastAPI server that also serves the React build |
| What AI does it use? | Google Gemini (gemini-3.5-flash) |
| What does AI do? | Match free-text to FAQs, write answers, detect special situations |
| What does AI NOT do? | Decide the flow, write safety responses, touch user data |
| How many languages? | 11 (English + 10 Indian languages in Roman script) |
| How are tickets created? | POST to Dostt API with FAQ ID, description, entity ref, consent |
| Max tickets per session? | 2 |
| Session duration? | 1 hour of inactivity |
| Is there a database? | No — sessions are in memory. FAQ data is in JSON files. |
| How do I test without hitting Dostt APIs? | Set DUMMY_MODE=true in .env |
| How do I switch staging/prod? | Set APP_ENV=staging or APP_ENV=production in .env |
