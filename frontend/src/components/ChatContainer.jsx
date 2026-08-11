import { useEffect, useRef } from "react";
import Message from "./Message";
import TypingIndicator from "./TypingIndicator";
import { t } from "../translations";

const INTERACTIVE_TYPES = new Set([
  "quick_replies", "category_cards", "faq_cards",
  "call_cards", "transaction_cards", "transaction_subtype_cards",
  "ticket_confirmation",
]);

export default function ChatContainer({
  messages,
  isLoading,
  language,
  viewportHeight,
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
  }, [messages, isLoading, viewportHeight]);

  // Only activate an interactive card if the very last message is itself interactive.
  // If the last message is text (e.g. edit prompt), all prior cards go stale.
  const lastMsg = messages[messages.length - 1];
  let lastInteractiveIdx = -1;
  if (lastMsg && INTERACTIVE_TYPES.has(lastMsg.type)) {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (INTERACTIVE_TYPES.has(messages[i].type)) { lastInteractiveIdx = i; break; }
    }
  }

  return (
    <div className="chat-container" role="log" aria-live="polite" aria-label="Conversation">
      <div className="date-divider"><span>{t(language, "today")}</span></div>
      {messages.map((msg, i) => (
        <Message
          key={msg.id}
          msg={msg}
          isActive={i === lastInteractiveIdx}
          language={language}
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
