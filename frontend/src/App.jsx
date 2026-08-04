import ChatContainer from "./components/ChatContainer";
import Header from "./components/Header";
import MessageInput from "./components/MessageInput";
import { useBridge } from "./hooks/useBridge";
import { useChat } from "./hooks/useChat";

export default function App() {
  const { token, userType } = useBridge();

  const {
    messages,
    isLoading,
    error,
    sendText,
    addUserMessage,
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
    sessionId,
  } = useChat(token, userType);

  function handleQuickReply(optionId, label) {
    if (optionId === "confirm_ticket") {
      if (label) addUserMessage(label);
      confirmTicket();
    } else if (optionId === "cancel") {
      if (label) addUserMessage(label);
      cancelAction();
    } else if (optionId === "consent_yes") {
      if (label) addUserMessage(label);
      consentYes();
    } else if (optionId === "consent_no") {
      if (label) addUserMessage(label);
      consentNo();
    } else if (optionId === "more_help_yes") {
      if (label) addUserMessage(label);
      moreHelpYes();
    } else if (optionId === "more_help_no") {
      if (label) addUserMessage(label);
      moreHelpNo();
    } else {
      // sendText handles its own appendUserMessage internally
      sendText(label || optionId);
    }
  }

  const loading = !sessionId && isLoading;

  const SELECTION_TYPES = [
    "category_cards",
    "transaction_subtype_cards",
    "faq_cards",
    "call_cards",
    "transaction_cards",
    "quick_replies",
    "ticket_confirmation",
    "chat_ended",
    "error",
  ];
  const lastBotMsg = [...messages].reverse().find((m) => m.role === "bot");
  const isChatEnded = lastBotMsg?.type === "chat_ended";
  const awaitingSelection = lastBotMsg && SELECTION_TYPES.includes(lastBotMsg.type);

  return (
    <div className="app">
      <Header />

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="loading-screen">
          <div className="loading-spinner" aria-label="Loading" />
          <span>Connecting to support…</span>
        </div>
      ) : (
        <ChatContainer
          messages={messages}
          isLoading={isLoading}
          onSelectCategory={selectCategory}
          onSelectTransactionSubtype={selectTransactionSubtype}
          onSelectFaq={selectFaq}
          onSelectCall={selectCall}
          onSelectTransaction={selectTransaction}
          onConfirmTicket={confirmTicket}
          onEditTicket={editTicket}
          onCancelAction={cancelAction}
          onQuickReply={handleQuickReply}
        />
      )}

      {sessionId && !loading && (
        <div className="restart-bar">
          <button className="restart-chip" onClick={restartChat} disabled={isLoading}>
            ↩ Restart chat
          </button>
        </div>
      )}

      <MessageInput
        onSend={sendText}
        disabled={isLoading || loading || awaitingSelection}
        placeholder={isChatEnded ? "This chat has ended" : awaitingSelection ? "Please select an option above" : "Type a message..."}
      />
    </div>
  );
}
