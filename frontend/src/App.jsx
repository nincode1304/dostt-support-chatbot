import ChatContainer from "./components/ChatContainer";
import Header from "./components/Header";
import MessageInput from "./components/MessageInput";
import { useBridge } from "./hooks/useBridge";
import { useChat } from "./hooks/useChat";
import { t } from "./translations";

export default function App() {
  const { token, userType, initLanguage, platform, appVersionCode, send: sendToNative } = useBridge();

  const {
    messages,
    isLoading,
    isTyping,
    error,
    language,
    setLanguage,
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
  } = useChat(token, userType, initLanguage, platform, appVersionCode);

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
      <Header language={language} onLanguageChange={setLanguage} initLanguage={initLanguage} />

      {error && <div className="error-banner">{error}</div>}

      {!!sessionId && !loading && (
        <div className="chat-top-bar">
          <button className="restart-pill-btn" onClick={restartChat} aria-label="Restart chat">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
            </svg>
            Restart chat
          </button>
        </div>
      )}

      {loading ? (
        <div className="loading-screen">
          <div className="loading-spinner" aria-label="Loading" />
          <span>{t(language, "connecting")}</span>
        </div>
      ) : (
        <ChatContainer
          messages={messages}
          isLoading={isLoading || isTyping}
          language={language}
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

      <MessageInput
        onSend={sendText}
        disabled={isLoading || loading || isTyping || awaitingSelection}
        placeholder={isChatEnded ? t(language, "chat_ended_placeholder") : awaitingSelection ? t(language, "select_option") : t(language, "type_message")}
      />
    </div>
  );
}
