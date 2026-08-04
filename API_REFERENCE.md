# Dostt Support Chatbot — API Reference

**Base URL:** `https://testdostt.getlokalapp.com`

All requests require these headers:

```
JWT-AUTHORIZATION: Bearer <token>
Service-Type: 1
Accept: application/json, text/plain, */*
app-version: 1.1.31
app-version-code: 131
X-Country-Code: IN
X-Pricing-Country-code: IN
X-Platform-Type: Android
```

---

## Data Fetch APIs

### 1. User — Recent Calls
**When:** User selects "Recent Calls" category

```
GET /help-and-support/bookings/customers/
```

Response fields used: `id`, `booking_date`, `type`, `session_id`, `booked_at`, `total_duration`, `duration`, `expert.name`, `coins`, `ticket_detail`

---

### 2. User — Coin Transactions
**When:** User selects "Recent Transactions" category

```
GET /help-and-support/bookings/transactions/
```

Response fields used: `id`, `amount`, `title`, `status`, `coins`, `created_on`, `ticket_detail`

---

### 3. Listener — Recent Sessions (Calls)
**When:** Listener selects "Recent Calls" category

```
GET /help-and-support/bookings/experts/
```

Response fields used: `id`, `booking_date`, `type`, `session_id`, `booked_at`, `total_duration`, `duration`, `customer.name`, `ticket_detail`

---

### 4. Listener — Earnings
**When:** Listener selects "Recent Transactions" → "My Earnings"

```
GET /help-and-support/payments/earnings/
```

Response fields used: `id`, `title`, `amount`, `status`, `created_on`, `ticket_detail`

---

### 5. Listener — Payouts / Withdrawals
**When:** Listener selects "Recent Transactions" → "My Payouts / Withdrawals"

```
GET /help-and-support/payments/payouts/
```

Response fields used: `id`, `title`, `amount`, `status`, `created_on`, `ticket_detail`

---

## Ticket Creation API

**When:** User confirms ticket creation at the end of the support flow

```
POST /help-and-support/tickets/
Content-Type: multipart/form-data
```

### Form Fields

| Field | Type | Description |
|---|---|---|
| `description` | string | Ticket description (user's issue or message) |
| `issues` | string | FAQ/issue ID (e.g. `"332"`) |
| `languages` | string | Language code — hardcoded `"2"` |
| `is_call_opted_in` | string | `"true"` or `"false"` — whether user agreed to a callback |
| `type` | string | Issue type from FAQ (`0`, `1`, `2`, `3`) |
| `reference_entity_id` | string | *(optional)* ID of the related call or transaction |
| `reference_entity_type` | string | *(optional)* `"booking"`, `"order"`, `"dosttexpertpayout"` |

### `reference_entity_type` logic

| Scenario | `reference_entity_type` |
|---|---|
| Call-related ticket (any user type) | `"booking"` |
| Transaction ticket — User | `"order"` |
| Transaction ticket — Listener (earnings) | `"booking"` |
| Transaction ticket — Listener (payouts) | `"dosttexpertpayout"` |
| No linked call/transaction | field omitted |

---

## Current Mode

`DUMMY_MODE = True` in `dostt_client.py` — no real API calls are made. Hardcoded sample data is returned for all fetch endpoints, and ticket creation logs a fake `TKT-XXXXXX` ID. Set to `False` to go live.
