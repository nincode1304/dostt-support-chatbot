# Dostt Support Chatbot — Full Product Description

---

## What is this?

The Dostt Support Chatbot is an in-app customer support tool embedded inside the Dostt mobile app as a WebView. When a user opens the Help & Support section, they land directly in this chatbot instead of a static FAQ page or an email form. The bot guides them through their issue, shows them relevant information pulled from their account, answers common questions using AI, and raises a support ticket on their behalf if needed — all without any human agent involvement.

---

## Who uses it?

There are two types of users:

**Users** — people who use the Dostt app to book audio calls with Listeners. Their support issues are typically about calls they made or money they spent (wallet recharges).

**Listeners** — people who receive calls on Dostt and earn money from them. Their support issues are typically about calls they received, earnings they made, or payouts (withdrawals) they requested.

The bot knows which type the person is from the moment the session starts and shows different options and FAQs based on that.

---

## How a session starts

When someone opens the chatbot, the Dostt app passes their auth token, user type (User or Listener), platform (Android/iOS), and app version to the chatbot backend. The backend creates a session and returns a greeting message along with the three main category cards. The session stays alive for the duration of that chat.

Language defaults to English every time a session starts or restarts. The user can switch to any of the 11 supported languages at any point using the language selector in the header.

---

## The three main paths

Every conversation starts with the user picking one of three categories:

1. **Recent Calls**
2. **Recent Transactions**
3. **Other Issues**

These are shown as tappable cards, not typed choices. The user cannot skip this step.

---

## Path 1 — Recent Calls

**Step 1: Fetch calls from the Dostt API**

The bot calls the Dostt backend using the user's auth token to get their recent calls. For Users, this is their call booking history. For Listeners, this is their expert session history. The bot filters out calls that already have an open support ticket (so the user cannot raise a duplicate) and shows up to 5 calls.

**Step 2: Handle edge cases**

- If the auth token is invalid (401 error), the bot shows a session error and ends the chat immediately.
- If there are no calls without existing tickets, the bot says "No recent activity found" and jumps to the "Anything else?" prompt.

**Step 3: User picks a call**

The user taps on one of the call cards. Each card shows the call date, the other person's name, duration, and cost in coins.

**Step 4: Show FAQ cards**

After picking a call, the bot shows a list of frequently reported issues related to calls (filtered to the user's type — User or Listener sees different issues). The user taps the one that best describes their problem.

**Step 5: AI generates an answer**

Gemini generates a contextual answer that includes details about the specific call the user selected (date, duration, cost). The answer is written in the user's selected language using Roman script for non-English languages.

**Step 6: Depending on the issue type, one of three things happens:**

- **Information only** — the bot answers and asks if there's anything else.
- **Raise ticket automatically** — the bot shows a ticket confirmation card immediately (no "still facing this?" question).
- **Raise ticket optionally** — the bot answers and asks "Still facing this issue?" Yes/No. If Yes, it goes to the ticket flow.

---

## Path 2 — Recent Transactions

For **Users**, this works almost identically to the Calls path but fetches wallet recharge transactions instead of calls.

For **Listeners**, there is an extra step: the bot first asks whether they want help with **Earnings** (money earned from calls) or **Payouts** (withdrawal requests). After choosing, the bot fetches the relevant records and shows up to 5 cards.

The rest of the flow — picking a record, seeing FAQs, getting an AI answer, optional ticket — is the same as the Calls path.

If no records exist or all have existing tickets, the bot says "No recent activity found" and moves on.

---

## Path 3 — Other Issues (free text)

This path handles anything that doesn't fit neatly into calls or transactions — account issues, profile problems, general app complaints, etc.

**Step 1: Bot asks user to describe their issue**

The user types freely in any language, any script (Hindi, Hinglish, Roman, Devanagari, Tamil script, etc.).

**Step 2: Mental health keyword check (instant, before AI)**

Before sending anything to AI, the backend checks the message against a hardcoded list of suicide and self-harm keywords. If matched, the bot immediately replies with the Tele-MANAS helpline number (1800-891-4416) and stays ready for the user's next message. This check never goes to Gemini — it is always instant.

**Step 3: Single Gemini call — intent + FAQ matching**

If the message is not a mental health flag, it goes to Gemini with the full list of FAQs. Gemini does two things in one call: it classifies the intent of the message AND identifies which FAQ (if any) best matches. It returns one of three outcomes:

- `SPECIAL:<category>` — the message is sensitive, off-topic, or needs a special response
- `FAQ:<id>` — the message matches a specific FAQ
- `UNKNOWN` — the message is app-related but no FAQ fits

**Step 4a: If SPECIAL**

There are 11 special categories. For each one, the bot returns a pre-written, pre-translated response. Gemini is NOT used to write these responses — Gemini only does the routing decision. The user stays in the free-text stage and can keep typing.

| Category | What triggers it | What the bot says |
|---|---|---|
| MENTAL_HEALTH | Suicide or self-harm | Tele-MANAS helpline |
| HARMFUL | Explicit sexual or violent content | Redirects to app-related issues |
| VERBAL_ABUSE | Profanity or insults | Acknowledges frustration, asks for the actual issue |
| PRIVACY_PROBING | Asking for user data or exploit methods | Cannot share private information |
| PROMPT_INJECTION | Trying to change bot identity or override instructions | Cannot follow in-chat instructions |
| SPAM_GIBBERISH | Random characters, keyboard mashing | Did not understand |
| OFF_TOPIC | Politics, cricket, recipes — not Dostt-related | Redirects to Dostt issues |
| LEGAL_THREAT | Explicitly threatening to sue | Email grievance.officer@dostt.in |
| CALL_REQUEST | Wants support to phone them back | Cannot arrange a call, can raise a ticket |
| SCAM_FRAUD | Claims they were scammed or platform is fraud | Will raise a ticket for investigation |
| MISINFORMATION | Claims to be Dostt staff or spreads false info | Official communications only through the app |

**Step 4b: If FAQ matched**

Gemini returns an FAQ ID. The bot looks up that FAQ. Depending on the FAQ's category type:

- **CALL-type FAQ** — the bot redirects into the Calls path (fetches the user's calls, user picks one, then the pre-matched FAQ is applied automatically — they skip the FAQ selection step).
- **PAYMENT-type FAQ** — same as above but for the Transactions path.
- **OTHER-type FAQ** — no call or transaction needed. Gemini answers directly.

**Step 4c: If UNKNOWN**

- First time: bot asks the user to rephrase.
- Second time (still no match): bot says it couldn't identify the issue and directs them to the Help & Support section. Then asks if there's anything else.

---

## The ticket flow

This applies after any AI answer where a ticket can be raised.

**Step 1: Confirmation card**

The bot shows a card with:
- The issue name (the FAQ title)
- The description (the user's original message, or their free-text from the Other flow)
- Three buttons: **Confirm**, **Edit**, **Cancel**

**Step 2: Edit (optional)**

If the user taps Edit, the bot asks them to type an updated description. Once they type it, the confirmation card is shown again with the new text.

**Step 3: Callback consent**

When the user taps Confirm, the bot asks: "Would you like a callback from our support team?" Yes or No. This is asked regardless of the answer — the consent flag is just recorded and submitted with the ticket.

If the current time is outside business hours (before 9am or after 7pm IST), an additional note is shown alongside the Yes/No buttons explaining that callbacks happen during business hours.

**Step 4: Ticket submitted**

The bot calls the Dostt ticketing API with:
- The FAQ ID (which identifies the issue type)
- The description text
- A reference to the specific call or transaction the user selected (if any)
- The callback consent flag

On success, a ticket created card is shown with the ticket ID. On failure, the API's error message is shown directly.

**Ticket limit:** A user can raise maximum 2 tickets per chat session. If they hit the limit, the bot tells them and moves on.

---

## After any answer — "Anything else?"

After every resolved path (answered, ticket created, no recent activity, content safety response), the bot asks "Is there anything else I can help you with?" with Yes/No buttons.

- **Yes** → back to the three category cards, fresh start
- **No** → "Thank you. You may close this chat." The input box is disabled.

The user can also tap the "Restart chat" button at the top at any time, which does the same thing as answering "Yes" to anything else.

---

## Language support

The bot supports 11 languages: English, Hindi, Tamil, Telugu, Malayalam, Kannada, Marathi, Punjabi, Bengali, Gujarati, Odia.

All bot UI text (buttons, prompts, error messages, pre-written safety responses) is pre-translated into all 11 languages. These are static translations — no AI is used for them.

AI-generated answers (the actual FAQ responses) are generated by Gemini in the user's selected language, always in Roman script for non-English languages (no Devanagari, no Tamil script in AI responses — to keep text readable across devices).

Gemini understands user input in any script or any language regardless of what language the bot is set to. If a user types in Devanagari, Kannada script, Hinglish, or broken English, Gemini still understands and responds correctly.

---

## What AI does and does not do

**AI (Gemini) is responsible for:**
- Classifying what the user's free-text message is about and routing it to the right FAQ
- Writing the actual support answer for a given FAQ, personalised with the specific call or transaction the user selected
- Detecting whether a user's response at the "Still facing this issue?" stage means they want a ticket or not

**AI is NOT responsible for:**
- Deciding which stage of the conversation to move to (that is all deterministic code)
- Writing safety responses (pre-written, pre-translated)
- Deciding whether to raise a ticket (determined by the FAQ's feedback_type field)
- Fetching data from Dostt APIs
- Anything that touches user data directly

This means: if Gemini is down, the structured parts of the bot (call selection, transaction selection, FAQ browsing, ticket submission) still work. Only the "Other Issues" free-text path and the answer-generation step require Gemini.

---

## Key rules and limits

- **Session language** always defaults to English on open and restart. It only changes when the user explicitly picks a different language.
- **Duplicate tickets** are prevented by filtering out calls and transactions that already have an open ticket before showing them.
- **Ticket limit** is 2 per session. After 2, the ticket option is suppressed and the user is moved on.
- **401 on any API call** immediately ends the session with an error. The user has to re-open the chatbot from the app (which will pass a fresh token).
- **No data fallback**: if calls or transactions exist but cannot be fetched, the FAQ list is shown without a pre-selected entity, and the AI answers without entity context.
- **Restart** at any point takes the user back to the three category cards, clears all selected data, but keeps the same session (tickets raised count carries over).

---

## Conversation flow diagram

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

## Stage reference

| Stage | What it means |
|---|---|
| `AWAITING_CATEGORY_SELECTION` | Session just started or restarted — showing the 3 category cards |
| `AWAITING_CALL_SELECTION` | Calls were fetched successfully — user needs to pick one |
| `AWAITING_TRANSACTION_SUBTYPE` | LISTENER picked Transactions — needs to choose Earnings or Payouts |
| `AWAITING_TRANSACTION_SELECTION` | Transactions/earnings/payouts fetched — user needs to pick one |
| `AWAITING_FAQ_SELECTION` | Call or transaction selected — user needs to pick which issue |
| `AWAITING_OTHER_TEXT` | User picked Other Issues — waiting for free-text input |
| `ANSWERED` | Bot answered — waiting to see if user still has the issue (for BOTH type FAQs) |
| `AWAITING_TICKET_CONFIRMATION` | Showing the confirm/edit/cancel ticket card |
| `AWAITING_TICKET_EDIT` | User tapped Edit — waiting for their new description text |
| `AWAITING_CALL_CONSENT` | Ticket confirmed — asking about callback preference |
| `AWAITING_MORE_HELP_RESPONSE` | After any terminal response — asking if they need anything else |
| `ENDED` | User said No to more help — chat is closed |
