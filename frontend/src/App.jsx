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
    selectCall,
    selectTransaction,
    confirmTicket,
    editTicket,
    cancelAction,
    consentYes,
    consentNo,
    sessionId,
  } = useChat(token, userType);

  function handleQuickReply(optionId) {
    if (optionId === "confirm_ticket") {
      confirmTicket();
    } else if (optionId === "cancel") {
      cancelAction();
    } else if (optionId === "consent_yes") {
      consentYes();
    } else if (optionId === "consent_no") {
      consentNo();
    } else {
      sendText(optionId);
    }
  }

  const loading = !sessionId && isLoading;

  const SELECTION_TYPES = ["call_cards", "transaction_cards", "quick_replies", "ticket_confirmation"];
  const lastBotMsg = [...messages].reverse().find((m) => m.role === "bot");
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
          onSelectCall={selectCall}
          onSelectTransaction={selectTransaction}
          onConfirmTicket={confirmTicket}
          onEditTicket={editTicket}
          onCancelAction={cancelAction}
          onQuickReply={handleQuickReply}
        />
      )}

      <MessageInput onSend={sendText} disabled={isLoading || loading || awaitingSelection} placeholder={awaitingSelection ? "Please select an option above" : "Type a message..."} />
    </div>
  );
}
