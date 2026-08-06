export const AnalyticsEvents = {
  SESSION_STARTED:    "support_session_started",
  SESSION_TERMINATED: "support_session_terminated",
  TICKET_CREATED:     "support_ticket_created",
};

export function logEvent(eventName, params = {}) {
  try {
    const payload = { name: eventName, ...params };
    if (window.ReactNativeWebView?.postMessage) {
      window.ReactNativeWebView.postMessage(JSON.stringify({ name: "analytics", payload }));
    }
    console.log("[Analytics]", eventName, params);
  } catch (e) {
    console.error("[Analytics] Error logging event:", e);
  }
}
