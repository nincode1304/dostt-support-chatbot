# Dostt Support Chatbot — Conversation Flow

```mermaid
flowchart TD

    %% ── Entry ─────────────────────────────────────────────────────────────
    START([User opens chatbot])
    START --> INIT[Session initialised\nLanguage: English]
    INIT --> CATS

    %% ── Category selection ────────────────────────────────────────────────
    CATS{{"Select a category"}}
    CATS -->|Recent Calls| FETCH_CALLS
    CATS -->|Recent Transactions| TX_TYPE
    CATS -->|Other Issues| OTHER_INPUT

    %% ══════════════════════════════════════════════════════════════════════
    %% CALLS BRANCH
    %% ══════════════════════════════════════════════════════════════════════

    FETCH_CALLS["Fetch calls from API\n(USER → bookings/customers\nLISTENER → bookings/experts)"]
    FETCH_CALLS --> CALLS_401{401 error?}
    CALLS_401 -->|Yes| SESSION_ERR[/"⚠ Session error\n→ END"/]
    CALLS_401 -->|No| CALLS_EMPTY{0 calls\nwithout ticket?}
    CALLS_EMPTY -->|Yes| NO_ACT_C[/"No recent activity found"/]
    NO_ACT_C --> MORE_HELP
    CALLS_EMPTY -->|No| SHOW_CALLS["Show up to 5 call cards"]
    SHOW_CALLS --> PICK_CALL[User selects a call]
    PICK_CALL --> PRE_FAQ_C{Preselected FAQ\nfrom Other flow?}
    PRE_FAQ_C -->|Yes| GEN_SEL
    PRE_FAQ_C -->|No| CALL_FAQS

    %% ══════════════════════════════════════════════════════════════════════
    %% TRANSACTIONS BRANCH
    %% ══════════════════════════════════════════════════════════════════════

    TX_TYPE{User type?}
    TX_TYPE -->|USER| FETCH_TX
    TX_TYPE -->|LISTENER| TX_SUBTYPE

    TX_SUBTYPE{{"Choose:\nEarnings or Payouts?"}}
    TX_SUBTYPE -->|My Earnings| FETCH_EARN
    TX_SUBTYPE -->|My Payouts| FETCH_PAY

    FETCH_TX["Fetch transactions\npayments/transactions\n(Wallet Recharge only)"]
    FETCH_TX --> TX_401{401?}
    TX_401 -->|Yes| SESSION_ERR
    TX_401 -->|No| TX_EMPTY{0 transactions?}
    TX_EMPTY -->|Yes| NO_ACT_T[/"No recent activity found"/]
    NO_ACT_T --> MORE_HELP
    TX_EMPTY -->|No| SHOW_TX["Show up to 5 transaction cards"]

    FETCH_EARN["Fetch earnings\npayments/earnings"]
    FETCH_EARN --> EARN_401{401?}
    EARN_401 -->|Yes| SESSION_ERR
    EARN_401 -->|No| EARN_EMPTY{0 earnings?}
    EARN_EMPTY -->|Yes| NO_ACT_E[/"No recent activity found"/]
    NO_ACT_E --> MORE_HELP
    EARN_EMPTY -->|No| SHOW_TX

    FETCH_PAY["Fetch payouts\npayments/payouts"]
    FETCH_PAY --> PAY_401{401?}
    PAY_401 -->|Yes| SESSION_ERR
    PAY_401 -->|No| PAY_EMPTY{0 payouts?}
    PAY_EMPTY -->|Yes| NO_ACT_P[/"No recent activity found"/]
    NO_ACT_P --> MORE_HELP
    PAY_EMPTY -->|No| SHOW_TX

    SHOW_TX["Show up to 5 transaction cards"]
    SHOW_TX --> PICK_TX[User selects a transaction]
    PICK_TX --> PRE_FAQ_T{Preselected FAQ\nfrom Other flow?}
    PRE_FAQ_T -->|Yes| GEN_SEL
    PRE_FAQ_T -->|No| CALL_FAQS

    %% ══════════════════════════════════════════════════════════════════════
    %% FAQ SELECTION
    %% ══════════════════════════════════════════════════════════════════════

    CALL_FAQS["Show FAQ cards\n(filtered by category & user type)"]
    CALL_FAQS --> PICK_FAQ[User selects an FAQ]

    PICK_FAQ --> HAS_ENTITY{Call or transaction\nselected?}
    HAS_ENTITY -->|Yes| GEN_SEL
    HAS_ENTITY -->|No — no data was available| GEN_NODATA

    GEN_SEL["Gemini: generate answer\nin context of selected item"]
    GEN_NODATA["Gemini: generate answer\n(no entity context)"]

    GEN_SEL --> FEEDBACK
    GEN_NODATA --> FEEDBACK

    %% ══════════════════════════════════════════════════════════════════════
    %% OTHER / FREE TEXT BRANCH
    %% ══════════════════════════════════════════════════════════════════════

    OTHER_INPUT[User types free-text message]

    %% ── Step 1: mental-health keyword guard (no AI round-trip) ───────────
    OTHER_INPUT --> MH_CHECK{Mental health\nkeyword?}
    MH_CHECK -->|Yes| MH_RESP[/"Helpline message\n(Tele-MANAS 1800-891-4416)"\nStay in AWAITING_OTHER_TEXT/]
    MH_RESP --> OTHER_INPUT

    %% ── Step 2: single Gemini call — intent + FAQ in one pass ────────────
    MH_CHECK -->|No| AI_INTENT["Gemini: identify_other_intent\n(intent + FAQ in one call)"]
    AI_INTENT --> INTENT{Intent?}

    %% ── SPECIAL branch ───────────────────────────────────────────────────
    INTENT -->|SPECIAL| SPEC_TYPE{Category?}

    SPEC_TYPE -->|HARMFUL| S_HARMFUL[/"Redirect to app issues"\nStay in AWAITING_OTHER_TEXT/]
    SPEC_TYPE -->|VERBAL_ABUSE| S_ABUSE[/"Acknowledge upset, ask for issue"\nStay in AWAITING_OTHER_TEXT/]
    SPEC_TYPE -->|PRIVACY_PROBING| S_PRIV[/"Cannot share private info"\nStay in AWAITING_OTHER_TEXT/]
    SPEC_TYPE -->|PROMPT_INJECTION| S_INJECT[/"Cannot follow chat instructions"\nStay in AWAITING_OTHER_TEXT/]
    SPEC_TYPE -->|SPAM_GIBBERISH| S_SPAM[/"Did not understand"\nStay in AWAITING_OTHER_TEXT/]
    SPEC_TYPE -->|OFF_TOPIC| S_OFF[/"Redirect to Dostt issues"\nStay in AWAITING_OTHER_TEXT/]
    SPEC_TYPE -->|LEGAL_THREAT| S_LEGAL[/"Email grievance.officer@dostt.in"\nStay in AWAITING_OTHER_TEXT/]
    SPEC_TYPE -->|CALL_REQUEST| S_CALL[/"Cannot arrange call, can raise ticket"\nStay in AWAITING_OTHER_TEXT/]
    SPEC_TYPE -->|SCAM_FRAUD| S_SCAM[/"Will raise ticket for investigation"\nStay in AWAITING_OTHER_TEXT/]
    SPEC_TYPE -->|MISINFORMATION| S_MISINFO[/"Official messages via app only"\nStay in AWAITING_OTHER_TEXT/]

    S_HARMFUL --> OTHER_INPUT
    S_ABUSE --> OTHER_INPUT
    S_PRIV --> OTHER_INPUT
    S_INJECT --> OTHER_INPUT
    S_SPAM --> OTHER_INPUT
    S_OFF --> OTHER_INPUT
    S_LEGAL --> OTHER_INPUT
    S_CALL --> OTHER_INPUT
    S_SCAM --> OTHER_INPUT
    S_MISINFO --> OTHER_INPUT

    %% ── FAQ branch ───────────────────────────────────────────────────────
    INTENT -->|FAQ| MATCH{FAQ type?}

    MATCH -->|No match — 1st attempt| REPHRASE[/"Could you rephrase?"/]
    REPHRASE --> OTHER_INPUT

    MATCH -->|No match — 2nd attempt| CANT_ID[/"Cannot identify issue\n→ direct to Help & Support"/]
    CANT_ID --> MORE_HELP

    MATCH -->|CALL type FAQ| REDIR_CALL["Redirect → Calls flow\n(FAQ preselected)"]
    REDIR_CALL --> FETCH_CALLS

    MATCH -->|PAYMENT type FAQ| REDIR_TX["Redirect → Transactions flow\n(FAQ preselected)"]
    REDIR_TX --> TX_TYPE

    MATCH -->|OTHER type FAQ| GEN_OTHER["Gemini: generate answer\n(no entity needed)"]
    GEN_OTHER --> FEEDBACK

    %% ── UNKNOWN branch ───────────────────────────────────────────────────
    INTENT -->|UNKNOWN — 1st attempt| REPHRASE
    INTENT -->|UNKNOWN — 2nd attempt| CANT_ID

    %% ══════════════════════════════════════════════════════════════════════
    %% FEEDBACK / POST-ANSWER
    %% ══════════════════════════════════════════════════════════════════════

    FEEDBACK{feedback_type?}

    FEEDBACK -->|FEEDBACK_ONLY| MORE_HELP
    FEEDBACK -->|RAISE_COMPLAINT_ONLY| TCK_LIMIT_A{Ticket limit\nreached?}
    FEEDBACK -->|BOTH| STILL_Q[/"Still facing this issue?"\nYes · No"/]

    TCK_LIMIT_A -->|Yes| LIMIT_MSG_A[/"Ticket limit reached"/]
    LIMIT_MSG_A --> MORE_HELP
    TCK_LIMIT_A -->|No| TICKET_CONFIRM

    STILL_Q -->|No — resolved| GLAD[/"Great, glad we could help!"/]
    GLAD --> MORE_HELP
    STILL_Q -->|Yes — still issue| TCK_LIMIT_B{Ticket limit\nreached?}
    TCK_LIMIT_B -->|Yes| LIMIT_MSG_B[/"Ticket limit reached"/]
    LIMIT_MSG_B --> MORE_HELP
    TCK_LIMIT_B -->|No| TICKET_CONFIRM

    %% ══════════════════════════════════════════════════════════════════════
    %% TICKET FLOW
    %% ══════════════════════════════════════════════════════════════════════

    TICKET_CONFIRM[/"Ticket confirmation card\nIssue · Description\nConfirm · Edit · Cancel"/]
    TICKET_CONFIRM -->|Cancel| TCK_CANCELLED[/"Ticket cancelled"/]
    TCK_CANCELLED --> MORE_HELP
    TICKET_CONFIRM -->|Edit| EDIT_PROMPT[/"Please type updated description"/]
    EDIT_PROMPT --> USER_EDITS[User types new description]
    USER_EDITS --> TICKET_CONFIRM

    TICKET_CONFIRM -->|Confirm| CONSENT[/"Would you like a callback call?\nYes · No"/]
    CONSENT --> SUBMIT["POST /tickets\nwith FAQ ID, description,\nentity reference, consent flag"]
    SUBMIT --> TCK_OK[/"Ticket created card\n(ticket ID shown)"/]
    TCK_OK --> MORE_HELP

    %% ══════════════════════════════════════════════════════════════════════
    %% MORE HELP
    %% ══════════════════════════════════════════════════════════════════════

    MORE_HELP[/"Is there anything else I can help with?\nYes · No"/]
    MORE_HELP -->|Yes| RESTART[/"Of course! What would you like help with?"/]
    RESTART --> CATS
    MORE_HELP -->|No| ENDED([/"Thank you. You may close the chat."/])

    %% ══════════════════════════════════════════════════════════════════════
    %% Styles
    %% ══════════════════════════════════════════════════════════════════════

    classDef api    fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a
    classDef bot    fill:#f0fdf4,stroke:#22c55e,color:#14532d
    classDef end_n  fill:#fef2f2,stroke:#ef4444,color:#7f1d1d
    classDef gate   fill:#fefce8,stroke:#eab308,color:#713f12
    classDef safety fill:#fdf4ff,stroke:#a855f7,color:#581c87

    class FETCH_CALLS,FETCH_TX,FETCH_EARN,FETCH_PAY,SUBMIT api
    class NO_ACT_C,NO_ACT_T,NO_ACT_E,NO_ACT_P,REPHRASE,CANT_ID,TCK_CANCELLED,GLAD,TCK_OK,CONSENT bot
    class SESSION_ERR,ENDED end_n
    class CATS,FEEDBACK,TX_SUBTYPE gate
    class MH_RESP,S_HARMFUL,S_ABUSE,S_PRIV,S_INJECT,S_SPAM,S_OFF,S_LEGAL,S_CALL,S_SCAM,S_MISINFO safety
```

---

## Stage Reference

| Stage | Triggered by |
|---|---|
| `AWAITING_CATEGORY_SELECTION` | Session init or restart |
| `AWAITING_CALL_SELECTION` | User picks "Recent Calls" and calls exist |
| `AWAITING_TRANSACTION_SUBTYPE` | LISTENER picks "Recent Transactions" |
| `AWAITING_TRANSACTION_SELECTION` | Transactions / earnings / payouts fetched |
| `AWAITING_FAQ_SELECTION` | Call or transaction selected (or no data — shows FAQs directly) |
| `AWAITING_OTHER_TEXT` | User picks "Other Issues" |
| `ANSWERED` | Bot answered — waiting to see if user wants a ticket (`BOTH` FAQ type) |
| `AWAITING_TICKET_CONFIRMATION` | `RAISE_COMPLAINT_ONLY` FAQ or user confirmed in `BOTH` |
| `AWAITING_TICKET_EDIT` | User clicks Edit on the ticket confirmation card |
| `AWAITING_CALL_CONSENT` | User confirms the ticket — ask for callback consent |
| `AWAITING_MORE_HELP_RESPONSE` | After any terminal bot response |
| `ENDED` | User said No to more help |

## Key Rules

- **Language** defaults to English on every session open and restart. Only changes on explicit user selection.
- **No activity** → "No recent activity found" → goes straight to More Help (no FAQ cards shown).
- **Ticket limit**: max 2 tickets per chat session. Hitting the limit skips ticket creation and goes to More Help.
- **Preselected FAQ**: when free-text matches a CALL or PAYMENT FAQ, the user is guided through the call/transaction selection first, then the FAQ answer is shown in context.
- **401 on any API call** → session error message → chat ends immediately.
- **Retry on Other**: first AI miss (UNKNOWN) → rephrase prompt. Second miss → cannot identify → More Help.

## Other Flow — Content Safety

The Other flow uses a single Gemini call (`identify_other_intent`) that simultaneously classifies intent and matches FAQs.

**Step 1 — Mental health keyword guard** (runs before any AI call):
Regex checks for suicide/self-harm keywords. On match → hardcoded helpline response immediately. Retry counter is reset so the next genuine message gets a full quota.

**Step 2 — Gemini intent routing** (one call, three outcomes):

| Outcome | Condition | Action |
|---|---|---|
| `SPECIAL` | Sensitive or off-topic content | Return predefined translated response, stay in `AWAITING_OTHER_TEXT`, reset retry |
| `FAQ` | Genuine app issue matching a known FAQ | Route to CALL / PAYMENT / OTHER FAQ flow |
| `UNKNOWN` | App-related but no FAQ match | Retry logic (rephrase → cannot identify) |

**Special categories and their responses:**

| Category | Response |
|---|---|
| `MENTAL_HEALTH` | Helpline message — Tele-MANAS 1800-891-4416 |
| `HARMFUL` | Redirect to app issues |
| `VERBAL_ABUSE` | Acknowledge upset, ask to describe the issue |
| `PRIVACY_PROBING` | Cannot share private information |
| `PROMPT_INJECTION` | Cannot follow in-chat instructions |
| `SPAM_GIBBERISH` | Did not understand the message |
| `OFF_TOPIC` | Redirect to Dostt-related issues |
| `LEGAL_THREAT` | Email grievance.officer@dostt.in |
| `CALL_REQUEST` | Cannot arrange a call, but can raise a ticket |
| `SCAM_FRAUD` | Will raise a ticket for investigation |
| `MISINFORMATION` | Official communications come through the app only |

All special responses are pre-translated into all 11 supported languages. Gemini never generates the text for these — only the routing decision is AI-driven.
