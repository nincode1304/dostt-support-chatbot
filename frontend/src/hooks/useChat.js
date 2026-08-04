import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE = "/api";

export function useChat(token, userType) {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const initialized = useRef(false);

  // Init session on mount
  useEffect(() => {
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
          body: JSON.stringify({ auth_token: tok, user_type: ut }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setSessionId(data.session_id);
        appendBotText(data.greeting);
        processResponseItems(data.items || []);
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

  const restartChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setIsLoading(true);
    initSession(token, userType);
  }, [initSession, token, userType]);

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

  function processResponseItems(items) {
    if (!items?.length) return;
    items.forEach((item, i) => {
      setTimeout(() => {
        setMessages((prev) => [...prev, { id: uid(), role: "bot", ...item }]);
      }, i * 300);
    });
    if (items.some((item) => item.type === "error")) {
      const tok = token;
      const ut = userType;
      setTimeout(() => {
        setMessages([]);
        setSessionId(null);
        setIsLoading(true);
        initSession(tok, ut);
      }, 5000);
    }
  }

  return {
    messages,
    isLoading,
    error,
    sessionId,
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
