# Dostt Support Chatbot — Conversation Flowchart

```mermaid
flowchart TD

%% ─────────────────────────────────────────────────────────────
%% 1. SESSION START
%% ─────────────────────────────────────────────────────────────

A([User opens Help & Support])
A --> B[App sends: auth token · user type · platform · app version]
B --> C[Backend creates session · Language = English]
C --> D[/Greeting message/]
D --> CAT

%% ─────────────────────────────────────────────────────────────
%% 2. CATEGORY SELECTION
%% ─────────────────────────────────────────────────────────────

CAT{{Pick a category}}
CAT -->|Recent Calls| CALLS
CAT -->|Recent Transactions| TX
CAT -->|Other Issues| OTHER

LANG([User switches language anytime])
LANG --> CAT

RESTART([User taps Restart anytime])
RESTART --> CAT

%% ─────────────────────────────────────────────────────────────
%% 3A. CALLS BRANCH
%% ─────────────────────────────────────────────────────────────

CALLS[Fetch recent calls from Dostt API\nUSER = call bookings · LISTENER = expert sessions\nExclude calls that already have a ticket · max 5]
CALLS --> C1{401 error?}
C1 -->|Yes| ERR[/Session expired · chat ends/]
C1 -->|No| C2{Any calls left?}
C2 -->|No| NOACT[/No recent activity found/]
NOACT --> MOREHELP
C2 -->|Yes| C3[/Show up to 5 call cards\ndate · name · duration · coins/]
C3 --> C4[User picks a call]
C4 --> C5{FAQ already matched\nfrom Other flow?}
C5 -->|Yes| GENANS
C5 -->|No| CFAQ[/Show FAQ cards for calls/]
CFAQ --> C6[User picks an FAQ]
C6 --> GENANS

%% ─────────────────────────────────────────────────────────────
%% 3B. TRANSACTIONS BRANCH
%% ─────────────────────────────────────────────────────────────

TX --> T0{User type?}
T0 -->|USER| TU[Fetch wallet recharge transactions · max 5 · no existing ticket]
T0 -->|LISTENER| TSUB

TSUB{{Earnings or Payouts?}}
TSUB -->|My Earnings| TE[Fetch listener earnings · max 5 · no existing ticket]
TSUB -->|My Payouts| TP[Fetch payout requests · max 5 · no existing ticket]

TU --> TU1{401?}
TE --> TE1{401?}
TP --> TP1{401?}
TU1 -->|Yes| ERR
TE1 -->|Yes| ERR
TP1 -->|Yes| ERR
TU1 -->|No| TU2{Any records?}
TE1 -->|No| TE2{Any records?}
TP1 -->|No| TP2{Any records?}
TU2 -->|No| NOACT
TE2 -->|No| NOACT
TP2 -->|No| NOACT

TU2 -->|Yes| TXSHOW
TE2 -->|Yes| TXSHOW
TP2 -->|Yes| TXSHOW

TXSHOW[/Show up to 5 transaction cards\ntype · amount · coins · status/]
TXSHOW --> T4[User picks a transaction]
T4 --> T5{FAQ already matched\nfrom Other flow?}
T5 -->|Yes| GENANS
T5 -->|No| TFAQ[/Show FAQ cards for transactions/]
TFAQ --> T6[User picks an FAQ]
T6 --> GENANS

%% ─────────────────────────────────────────────────────────────
%% 3C. OTHER ISSUES BRANCH
%% ─────────────────────────────────────────────────────────────

OTHER --> OP[/Please describe your issue\nany language · any script/]
OP --> UTYPE[User types message]

UTYPE --> MH{Mental health\nkeyword detected?}
MH -->|Yes — no AI, instant| MHR[/Tele-MANAS helpline: 1800-891-4416\nBot stays ready for next message/]
MHR --> UTYPE

MH -->|No| GEM[Gemini — identify_other_intent\nSees full FAQ list + user message + user type\nReturns one line only]

GEM --> INT{What did\nGemini return?}

INT -->|SPECIAL| SPE{Which\ncategory?}
SPE -->|MENTAL_HEALTH|       SR1[/Tele-MANAS helpline/]
SPE -->|HARMFUL|             SR2[/Keep messages about Dostt issues/]
SPE -->|VERBAL_ABUSE|        SR3[/We understand your frustration · describe the issue/]
SPE -->|PRIVACY_PROBING|     SR4[/Cannot share private information/]
SPE -->|PROMPT_INJECTION|    SR5[/Cannot follow in-chat instructions/]
SPE -->|SPAM_GIBBERISH|      SR6[/Did not understand · please rephrase/]
SPE -->|OFF_TOPIC|           SR7[/Can only help with Dostt app issues/]
SPE -->|LEGAL_THREAT|        SR8[/Email grievance.officer@dostt.in/]
SPE -->|CALL_REQUEST|        SR9[/Cannot arrange callback · can raise a ticket/]
SPE -->|SCAM_FRAUD|          SR10[/Will raise ticket for trust & safety team/]
SPE -->|MISINFORMATION|      SR11[/Official comms come only through the app/]

SR1 & SR2 & SR3 & SR4 & SR5 & SR6 & SR7 & SR8 & SR9 & SR10 & SR11 --> UTYPE

INT -->|FAQ matched| FTYPE{FAQ type?}
FTYPE -->|CALL type| REDIRC[Preselect FAQ · go to Calls path]
FTYPE -->|PAYMENT type| REDIRT[Preselect FAQ · go to Transactions path]
FTYPE -->|OTHER type| GENANS
REDIRC --> CALLS
REDIRT --> TX

INT -->|UNKNOWN| RET{Attempt\nnumber?}
RET -->|1st| REP[/Could you rephrase that?/]
REP --> UTYPE
RET -->|2nd| UNK[/Could not identify the issue\nPlease visit Help & Support in the app/]
UNK --> MOREHELP

%% ─────────────────────────────────────────────────────────────
%% 4. GEMINI GENERATES ANSWER  (all paths converge here)
%% ─────────────────────────────────────────────────────────────

GENANS[Gemini generates answer\nPersonalised with selected call / transaction details if available\nWritten in user language · Roman script for non-English]

GENANS --> FBT{FAQ feedback\ntype?}

%% ─────────────────────────────────────────────────────────────
%% 5. POST-ANSWER ROUTING
%% ─────────────────────────────────────────────────────────────

FBT -->|FEEDBACK_ONLY\nInfo-only FAQ| MOREHELP

FBT -->|RAISE_COMPLAINT_ONLY\nAlways needs ticket| TLIM1{Ticket limit\nreached?}
TLIM1 -->|Yes| TLIMR[/Max tickets reached for this session/]
TLIMR --> MOREHELP
TLIM1 -->|No| TCONF

FBT -->|BOTH\nAnswer + optional ticket| STILL[/Still facing this issue?\nYes · No/]
STILL -->|No — resolved| GLAD[/Glad we could help!/]
GLAD --> MOREHELP
STILL -->|Yes — needs ticket| TLIM2{Ticket limit\nreached?}
TLIM2 -->|Yes| TLIMR
TLIM2 -->|No| TCONF

%% ─────────────────────────────────────────────────────────────
%% 6. TICKET FLOW
%% ─────────────────────────────────────────────────────────────

TCONF[/Ticket confirmation card\nIssue name\nDescription — user original message\nConfirm · Edit · Cancel/]

TCONF -->|Cancel| TCAN[/Ticket cancelled/]
TCAN --> MOREHELP

TCONF -->|Edit| TEDIT[/Please type your updated description/]
TEDIT --> TEDITU[User types new description]
TEDITU --> TCONF

TCONF -->|Confirm| CONS[/Would you like a callback from support?\nYes · No\nIf outside 9am–7pm IST: off-hours note shown/]

CONS -->|Yes| SUB[POST /tickets\nFAQ ID · description · call or transaction reference · consent = true]
CONS -->|No| SUB2[POST /tickets\nFAQ ID · description · call or transaction reference · consent = false]

SUB --> SUBR{API response?}
SUB2 --> SUBR

SUBR -->|Success| TCREATED[/Ticket created · Ticket ID shown\nTrack it in Help & Support in the app/]
TCREATED --> MOREHELP

SUBR -->|Error| APIERR[/API error message shown · chat ends/]

%% ─────────────────────────────────────────────────────────────
%% 7. MORE HELP — all paths end here
%% ─────────────────────────────────────────────────────────────

MOREHELP[/Is there anything else I can help you with?\nYes · No/]
MOREHELP -->|Yes| BACKCAT[/Of course! What would you like help with?/]
BACKCAT --> CAT
MOREHELP -->|No| END([Thank you · You may close this chat\nInput disabled])

%% ─────────────────────────────────────────────────────────────
%% STYLES
%% ─────────────────────────────────────────────────────────────

classDef api     fill:#dbeafe,stroke:#3b82f6,color:#1e3a8a
classDef ai      fill:#ede9fe,stroke:#7c3aed,color:#2e1065
classDef gate    fill:#fefce8,stroke:#ca8a04,color:#713f12
classDef safe    fill:#fdf4ff,stroke:#a855f7,color:#581c87
classDef ticket  fill:#fff7ed,stroke:#ea580c,color:#7c2d12
classDef dead    fill:#fef2f2,stroke:#dc2626,color:#7f1d1d
classDef ok      fill:#f0fdf4,stroke:#16a34a,color:#14532d

class CALLS,TU,TE,TP,SUB,SUB2 api
class GEM,GENANS ai
class CAT,TSUB,T0,FBT,INT,SPE gate
class SR1,SR2,SR3,SR4,SR5,SR6,SR7,SR8,SR9,SR10,SR11,MHR safe
class TCONF,CONS,TCREATED ticket
class ERR,APIERR,END dead
class D,NOACT,GLAD,TLIMR,TCAN,BACKCAT ok
```

---

## Legend

| Colour | What it represents |
|---|---|
| Blue | API call to Dostt backend |
| Purple | Gemini AI call or AI-generated response |
| Yellow | Decision / branch point |
| Lilac | Content safety response (pre-written, no AI) |
| Orange | Ticket flow |
| Green | Positive bot response or end-of-step message |
| Red | Error state or chat end |
