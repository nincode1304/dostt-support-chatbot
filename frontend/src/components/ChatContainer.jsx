import { useEffect, useRef } from "react";
import Message from "./Message";
import TypingIndicator from "./TypingIndicator";

const INTERACTIVE_TYPES = new Set([
  "quick_replies", "category_cards", "faq_cards",
  "call_cards", "transaction_cards", "transaction_subtype_cards",
  "ticket_confirmation",
]);

export default function ChatContainer({
  messages,
  isLoading,
  onSelectCategory,
  onSelectTransactionSubtype,
  onSelectFaq,
  onSelectCall,
  onSelectTransaction,
  onConfirmTicket,
  onEditTicket,
  onCancelAction,
  onQuickReply,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Only the last interactive message in the list stays active
  let lastInteractiveIdx = -1;
  for (let i = messages.length - 1; i >= 0; i--) {
    if (INTERACTIVE_TYPES.has(messages[i].type)) { lastInteractiveIdx = i; break; }
  }

  return (
    <div className="chat-container" role="log" aria-live="polite" aria-label="Conversation">
      <div className="date-divider"><span>Today</span></div>
      {messages.map((msg, i) => (
        <Message
          key={msg.id}
          msg={msg}
          isActive={i === lastInteractiveIdx}
          onSelectCategory={onSelectCategory}
          onSelectTransactionSubtype={onSelectTransactionSubtype}
          onSelectFaq={onSelectFaq}
          onSelectCall={onSelectCall}
          onSelectTransaction={onSelectTransaction}
          onConfirmTicket={onConfirmTicket}
          onEditTicket={onEditTicket}
          onCancelAction={onCancelAction}
          onQuickReply={onQuickReply}
        />
      ))}
      {isLoading && <TypingIndicator />}
      <div ref={bottomRef} style={{ height: 8 }} />
    </div>
  );
}
