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
  const containerRef = useRef(null);

  // New messages / typing indicator → smooth scroll
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading]);

  // Keyboard open/close → instant jump so the bottom is immediately visible
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const raf = requestAnimationFrame(() => {
      el.scrollTo({ top: el.scrollHeight, behavior: "instant" });
    });
    return () => cancelAnimationFrame(raf);
  }, [viewportHeight]);

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
    <div ref={containerRef} className="chat-container" role="log" aria-live="polite" aria-label="Conversation">
      <div className="chat-spacer" />
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
      <div style={{ height: 8 }} />
    </div>
  );
}
