# Dostt Support Chatbot — Context Snapshot

## Project Overview
Full-stack AI customer support chatbot built for the Dostt app, served inside a WebView.
- **Backend**: Python FastAPI + Google Gemini (`gemini-2.5-flash` via `google-genai`)
- **Frontend**: React 18 + Vite
- **Branch**: `multi_language`

---

## Architecture

```
WebView (Android/iOS)
  └── INIT postMessage { token, language, platform, app_version_code }
        └── Frontend (React + Vite)
              └── REST API → Backend (FastAPI)
                    ├── Session management (in-memory)
                    ├── Gemini AI (intent/ticket description generation)
                    ├── FAQ matching (faq.json)
                    └── Dostt API client (calls, transactions, tickets)
```

---

## Languages Supported (11)
English, Hindi, Tamil, Telugu, Malayalam, Kannada, Marathi, Punjabi, Bengali, Gujarati, Odia
— All in **Roman script** only. UI strings translated; ticket card buttons stay English.

---

## Key Files

### Backend
| File | Purpose |
|------|---------|
| `backend/app/routers/chat.py` | Main conversation router — all flow logic |
| `backend/app/services/translations.py` | All bot strings for 11 languages via `t(language, key)` |
| `backend/app/services/faq_title_translations.py` | FAQ issue titles in 11 languages via `get_faq_title(faq_id, language, fallback)` |
| `backend/app/services/dostt_client.py` | Dostt API calls (calls, transactions, earnings, payouts, ticket creation) |
| `backend/app/services/session_service.py` | In-memory session store with TTL cleanup |
| `backend/app/services/ai_service.py` | Gemini integration for intent matching + ticket description |
| `backend/app/models/session.py` | `SessionState` — all conversation state |
| `backend/app/models/chat.py` | Request/response models, enums |
| `backend/app/services/faq_service.py` | FAQ loading and lookup from `faq.json` |

### Frontend
| File | Purpose |
|------|---------|
| `frontend/src/hooks/useChat.js` | All chat state, API calls, message processing |
| `frontend/src/hooks/useBridge.js` | WebView postMessage bridge (reads INIT token/language/platform) |
| `frontend/src/App.jsx` | Root component, wires all hooks and handlers |
| `frontend/src/components/Header.jsx` | Header with language dropdown + native-script letter badges |
| `frontend/src/components/MessageInput.jsx` | Text input bar + restart button |
| `frontend/src/components/ChatContainer.jsx` | Message list, active-card logic |
| `frontend/src/components/Message.jsx` | Renders all message types |
| `frontend/src/translations.js` | Frontend UI strings for 11 languages |
| `frontend/src/styles/globals.css` | All styles (design tokens → components) |

---

## Session Flow

```
INIT → create session (language, platform, app_version_code stored)
  → greeting + category cards

Category cards:
  ├── "Recent Calls"        → fetch 20 calls, filter ticketed, show top 5
  ├── "Recent Transactions" → fetch 20, filter ticketed + Wallet Recharge only, show top 5
  └── "Other Issues"        → FAQ list

For each selected entity:
  → AI matches FAQ → show FAQ cards
  → User selects FAQ → ticket description generated
  → Ticket confirmation → consent call → create ticket
```

---

## Data Fetch Strategy
All list endpoints fetch **limit=20** from the Dostt API, filter out entries that already have a `ticket_detail`, then cap display at **top 5**. This ensures ticketed entries don't consume the visible slots.

- **User transactions**: additionally filtered to `title == "Wallet Recharge"` only
- **Listener flows**: earnings + payouts use same 20→filter→5 approach

---

## Platform / Version Threading
WebView sends `platform` and `app_version_code` in the INIT message. These are:
1. Stored in `SessionState`
2. Passed to every Dostt API call via `_auth_headers(token, platform=..., app_version_code=...)`
3. Also forwarded in the `X-Platform-Type` and `app-version-code` HTTP headers

---

## Language Behaviour
- `SessionState.language` — source of truth
- `t(language, key, **kwargs)` — backend translation lookup
- `t(language, key)` — frontend translation lookup (translations.js)
- `get_faq_title(faq_id, language, fallback)` — FAQ title lookup (faq_title_translations.py)
- Language switch via `SET_LANGUAGE` message type
- If user switches language on step 1 (`AWAITING_CATEGORY_SELECTION`), chat reboots: clears messages and re-greets in new language

---

## UI Details
- **Favicon**: Dostt logo SVG on purple circle background
- **Bot avatar / typing indicator**: Dostt logo SVG
- **Message delay**: 500ms between bot messages
- **Restart button**: always active (not disabled during selection states)
- **Language dropdown**: borderless, purple letter badge (native script) + language name + chevron
- **Dropdown list**: each row has a 20px native-script letter circle
- **Tooltip**: "Try in your own language" — appears 0.6s after load, fades out after 2s (0.6s fade)
- **Category cards**: always in English for all languages ("Recent Calls", "Recent Transactions", "Other Issues")

---

## Native Script Letter Map (Header + Dropdown)
| Language | Letter |
|----------|--------|
| English | E |
| Hindi | ह |
| Tamil | த |
| Telugu | తె |
| Malayalam | മ |
| Kannada | ಕ |
| Marathi | म |
| Punjabi | ਪ |
| Bengali | ব |
| Gujarati | ગ |
| Odia | ଓ |

---

## DUMMY_MODE
`DUMMY_MODE = True` in `dostt_client.py` — no real Dostt API calls are made. Hardcoded dummy data is returned for calls, transactions, earnings, payouts. Set to `False` when a live token is available.

---

## Running Locally
```bash
# Backend
cd backend
pip3 install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## API Reference
See `API_REFERENCE.md` in project root for all Dostt endpoints, headers, and payload shapes.

---

## Security Note
Do not make unsolicited changes on `restricted_bot_branch`. All active work is on `multi_language`.
