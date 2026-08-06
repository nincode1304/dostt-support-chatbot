import { useCallback, useEffect, useRef, useState } from "react";
import { logEvent, AnalyticsEvents } from "../analytics";

const API_BASE = "/api";

export function useChat(token, userType, platform, appVersionCode) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState(null);
  const [language, setLanguageState] = useState("English");
  const languageRef = useRef("English");
  const initialized = useRef(false);

  // Init session once token arrives from the native bridge
  useEffect(() => {
    if (!token) return;
    if (initialized.current) return;
    initialized.current = true;
    initSession(token, userType);
  }, [token, userType]); // eslint-disable-line react-hooks/exhaustive-deps


  const initSession = useCallback(
    async (tok, ut) => {
      setIsLoading(true);
      try {
        const res = await fetch(`${API_BASE}/session/init`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ auth_token: tok, user_type: ut, language: languageRef.current, platform, app_version_code: appVersionCode }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setSessionId(data.session_id);
        logEvent(AnalyticsEvents.SESSION_STARTED, {
          session_id: data.session_id,
          user_type: ut,
          language: languageRef.current,
          platform,
        });
        processResponseItems([
          { type: "text", content: data.greeting },
          ...(data.items || []),
        ]);
      } catch (e) {
        setError("Could not connect to support. Please try again.");
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const sendMessage = useCallback(
    async (payload) => {
      if (!sessionId) return;
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, ...payload }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `HTTP ${res.status}`);
        }
        const data = await res.json();
        processResponseItems(data.items);
      } catch (e) {
        appendErrorMessage("Something went wrong. Please try again.");
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId]
  );

  // Convenience wrappers
  const sendText = useCallback(
    (text) => {
      appendUserMessage(text);
      sendMessage({ type: "text", message: text });
    },
    [sendMessage]
  );

  const selectCall = useCallback(
    (callId, label) => {
      if (label) appendUserMessage(label);
      sendMessage({ type: "select_call", selected_id: String(callId) });
    },
    [sendMessage]
  );

  const selectTransaction = useCallback(
    (txId, label) => {
      if (label) appendUserMessage(label);
      sendMessage({ type: "select_transaction", selected_id: String(txId) });
    },
    [sendMessage]
  );

  const confirmTicket = useCallback(
    () => sendMessage({ type: "confirm_ticket" }),
    [sendMessage]
  );

  const editTicket = useCallback(
    () => sendMessage({ type: "edit_ticket" }),
    [sendMessage]
  );

  const cancelAction = useCallback(
    () => sendMessage({ type: "cancel" }),
    [sendMessage]
  );

  const consentYes = useCallback(
    () => sendMessage({ type: "consent_yes" }),
    [sendMessage]
  );

  const consentNo = useCallback(
    () => sendMessage({ type: "consent_no" }),
    [sendMessage]
  );

  const moreHelpYes = useCallback(
    () => sendMessage({ type: "more_help_yes" }),
    [sendMessage]
  );

  const moreHelpNo = useCallback(
    () => sendMessage({ type: "more_help_no" }),
    [sendMessage]
  );

  const setLanguage = useCallback(
    async (lang) => {
      if (!sessionId) return;
      languageRef.current = lang;
      setLanguageState(lang);
      try {
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, type: "set_language", language: lang }),
        });
        if (!res.ok) return;
        const data = await res.json();
        // Backend returns items only when user is still on the first step — clear and re-greet
        if (data.items?.length) {
          setMessages([]);
          processResponseItems(data.items);
        }
      } catch {}
    },
    [sessionId]
  );

  const restartChat = useCallback(() => {
    logEvent(AnalyticsEvents.SESSION_TERMINATED, { session_id: sessionId, reason: "restart" });
    setMessages([]);
    setSessionId(null);
    setIsLoading(true);
    initSession(token, userType);
  }, [initSession, token, userType, sessionId]);

  const selectCategory = useCallback(
    (categoryId, label) => {
      if (label) appendUserMessage(label);
      sendMessage({ type: "select_category", selected_id: categoryId });
    },
    [sendMessage]
  );

  const selectTransactionSubtype = useCallback(
    (subtypeId, label) => {
      if (label) appendUserMessage(label);
      sendMessage({ type: "select_transaction_subtype", selected_id: subtypeId });
    },
    [sendMessage]
  );

  const selectFaq = useCallback(
    (faqId, label) => {
      if (label) appendUserMessage(label);
      sendMessage({ type: "select_faq", selected_id: String(faqId) });
    },
    [sendMessage]
  );

  // -------------------------------------------------------------------------
  // Message list helpers
  // -------------------------------------------------------------------------

  function appendUserMessage(text) {
    setMessages((prev) => [...prev, { id: uid(), role: "user", type: "text", content: text }]);
  }

  function appendBotText(text) {
    setMessages((prev) => [...prev, { id: uid(), role: "bot", type: "text", content: text }]);
  }

  function appendErrorMessage(text) {
    setMessages((prev) => [
      ...prev,
      { id: uid(), role: "bot", type: "error", content: text },
    ]);
  }

  const TYPING_DELAY = 1000;

  function processResponseItems(items) {
    if (!items?.length) return;
    setIsTyping(true);
    items.forEach((item, i) => {
      setTimeout(() => {
        setMessages((prev) => [...prev, { id: uid(), role: "bot", ...item }]);
        if (item.type === "ticket_created") {
          logEvent(AnalyticsEvents.TICKET_CREATED, {
            session_id: sessionId,
            ticket_id: item.data?.ticket_id ?? null,
            issue_name: item.data?.issue_name ?? null,
          });
        }
        if (i === items.length - 1) setIsTyping(false);
      }, (i + 1) * TYPING_DELAY);
    });
  }

  return {
    messages,
    isLoading,
    isTyping,
    error,
    sessionId,
    language,
    setLanguage,
    sendText,
    addUserMessage: appendUserMessage,
    moreHelpYes,
    moreHelpNo,
    restartChat,
    selectCategory,
    selectTransactionSubtype,
    selectFaq,
    selectCall,
    selectTransaction,
    confirmTicket,
    editTicket,
    cancelAction,
    consentYes,
    consentNo,
  };
}

let _counter = 0;
function uid() {
  return `msg_${Date.now()}_${_counter++}`;
}
