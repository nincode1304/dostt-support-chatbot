import { useEffect, useRef } from "react";
import Message from "./Message";
import TypingIndicator from "./TypingIndicator";

export default function ChatContainer({
  messages,
  isLoading,
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

  return (
    <div className="chat-container" role="log" aria-live="polite" aria-label="Conversation">
      <div className="date-divider">Today</div>
      {messages.map((msg) => (
        <Message
          key={msg.id}
          msg={msg}
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
