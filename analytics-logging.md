# Analytics Logging — How It Works

## The Simple Version

The chatbot runs inside a WebView (a browser window embedded inside the Dostt app).
The Dostt app is native (React Native).

These two environments **cannot talk to each other directly** — they are like two rooms with a wall between them.
The only way they can communicate is by **passing a string through a small hole in the wall**.

That hole is called the **bridge**.

---

## What Is an Analytics Event?

An analytics event is just a signal that says **"this thing happened"**.

Examples:
- A user opened the support chat → `support_session_started`
- A user raised a ticket → `support_ticket_created`
- A user restarted the chat → `support_session_terminated`

Each event has:
- A **name** — what happened
- **params** — extra details about what happened (who, when, which ticket, etc.)

---

## How Does Logging Actually Work?

### Step 1 — Something happens in the chatbot

For example, a ticket gets created. The code detects this and calls:

```js
logEvent("support_ticket_created", {
  session_id: "abc123",
  ticket_id: 1205930,
  issue_name: "Wrong charge on call"
})
```

### Step 2 — `logEvent` builds the message

`logEvent` lives in `frontend/src/analytics.js`. Here is what it does:

```js
export function logEvent(eventName, params = {}) {
  const payload = { name: eventName, ...params };

  // If inside the app → send to native through the bridge
  if (window.ReactNativeWebView?.postMessage) {
    window.ReactNativeWebView.postMessage(
      JSON.stringify({ name: "analytics", payload })
    );
  }

  // Always log to browser console (useful for local testing)
  console.log("[Analytics]", eventName, params);
}
```

It does two things:
1. Sends the event to the native app through the bridge (only when inside a WebView)
2. Prints it in the browser console so you can see it locally

### Step 3 — The bridge carries it to native

The bridge message looks like this (as a JSON string):

```json
{
  "name": "analytics",
  "payload": {
    "name": "support_ticket_created",
    "session_id": "abc123",
    "ticket_id": 1205930,
    "issue_name": "Wrong charge on call"
  }
}
```

`name: "analytics"` tells native — "this is an analytics event, handle it accordingly."
`payload` has the event name and all the extra details.

### Step 4 — Native receives it and sends to the dashboard

The native app (React Native) is already listening for bridge messages. When it receives a message with `name: "analytics"`, it picks it up and forwards it to Firebase / Mixpanel / whatever analytics tool Dostt uses.

**The chatbot doesn't need to know which analytics tool is being used.** It just says "here is an event" and native handles the rest. This is by design — same as how AI Dostt works.

---

## The Three Events We Log

### 1. `support_session_started`
**When:** Right after the session is successfully created (user opens the support chat)

**What it carries:**
```js
{
  session_id: "abc123",   // unique ID for this chat session
  user_type: "USER",      // USER or LISTENER
  language: "Hindi",      // language selected
  platform: "android"     // android or ios
}
```

---

### 2. `support_session_terminated`
**When:** User taps "Restart chat"

**What it carries:**
```js
{
  session_id: "abc123",
  reason: "restart"       // why the session ended
}
```

---

### 3. `support_ticket_created`
**When:** The ticket is successfully raised and the success card appears on screen

**What it carries:**
```js
{
  session_id: "abc123",
  ticket_id: 1205930,               // the real ticket ID from the API
  issue_name: "Wrong charge on call" // the issue the user raised
}
```

---

## Where Does Each Event Fire?

All three fire from `frontend/src/hooks/useChat.js`:

```
Session started   →  inside initSession()       — after API returns session_id
Session terminated → inside restartChat()       — before the session is cleared
Ticket created    →  inside processResponseItems() — when ticket_created message appears
```

---

## How to Add a New Event

### 1. Add the name in `analytics.js`

```js
export const AnalyticsEvents = {
  SESSION_STARTED:    "support_session_started",
  SESSION_TERMINATED: "support_session_terminated",
  TICKET_CREATED:     "support_ticket_created",
  CHAT_CANCELLED:     "support_chat_cancelled",   // ← new one
};
```

### 2. Call `logEvent` wherever it happens

```js
import { logEvent, AnalyticsEvents } from "../analytics";

logEvent(AnalyticsEvents.CHAT_CANCELLED, {
  session_id: sessionId,
  stage: "ticket_review"
});
```

That's it. Native already handles it — no changes needed on the app side.

---

## What Happens on Localhost?

`window.ReactNativeWebView` does not exist on a normal browser — there is no native app around the page.

So `logEvent` just skips the bridge step and prints to the console instead:

```
[Analytics] support_session_started { session_id: "dev", user_type: "USER", ... }
```

You can open the browser DevTools → Console tab and watch events fire in real time while testing.

---

## File Map

```
frontend/src/analytics.js          → logEvent() function + AnalyticsEvents constants
frontend/src/hooks/useChat.js      → where the three events are fired
frontend/src/hooks/useBridge.js    → the bridge (send + receive between WebView and native)
```
