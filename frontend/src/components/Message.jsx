import CallSelector from "./CallSelector";
import CategorySelector from "./CategorySelector";
import FaqSelector from "./FaqSelector";
import QuickReplies from "./QuickReplies";
import TicketConfirmation from "./TicketConfirmation";
import TransactionSelector from "./TransactionSelector";
import TransactionSubtypeSelector from "./TransactionSubtypeSelector";

function formatTime(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });
}

function renderContent(text) {
  // Break inline numbered items onto their own lines: " 1. Something" → newline before "1."
  const formatted = text.replace(/ (?=\d{1,2}\. [A-Z])/g, "\n");
  const lines = formatted.split("\n").filter((l) => l.trim() !== "");
  if (lines.length <= 1) return text;
  return lines.map((line, i) => (
    <span key={i} className="msg-line">{line.trim()}</span>
  ));
}

export default function Message({ msg, onSelectCategory, onSelectTransactionSubtype, onSelectFaq, onSelectCall, onSelectTransaction, onConfirmTicket, onEditTicket, onCancelAction, onQuickReply }) {
  const now = Date.now();

  if (msg.type === "text" || msg.type === "chat_ended") {
    return (
      <div className={`message-row ${msg.role}${msg.role === "bot" && msg.type === "error" ? " message-error" : ""}`}>
        {msg.role === "bot" && (
          <div className="bot-avatar">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
            </svg>
          </div>
        )}
        <div>
          <div className="message-bubble">{renderContent(msg.content)}</div>
          <div className="message-time">{formatTime(now)}</div>
        </div>
      </div>
    );
  }

  if (msg.type === "error") {
    return (
      <div className="message-row bot message-error">
        <div className="bot-avatar">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
          </svg>
        </div>
        <div>
          <div className="message-bubble">{msg.content}</div>
          <div className="message-time">{formatTime(now)}</div>
        </div>
      </div>
    );
  }

  if (msg.type === "category_cards") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <CategorySelector data={msg.data || {}} onSelect={onSelectCategory} />
      </div>
    );
  }

  if (msg.type === "transaction_subtype_cards") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <TransactionSubtypeSelector data={msg.data || {}} onSelect={onSelectTransactionSubtype} />
      </div>
    );
  }

  if (msg.type === "faq_cards") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <FaqSelector data={msg.data || {}} onSelect={onSelectFaq} />
      </div>
    );
  }

  if (msg.type === "call_cards") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <CallSelector data={msg.data || {}} onSelect={onSelectCall} />
      </div>
    );
  }

  if (msg.type === "transaction_cards") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <TransactionSelector data={msg.data || {}} onSelect={onSelectTransaction} />
      </div>
    );
  }

  if (msg.type === "ticket_confirmation") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <TicketConfirmation
          data={msg.data || {}}
          onConfirm={onConfirmTicket}
          onEdit={onEditTicket}
          onCancel={onCancelAction}
        />
      </div>
    );
  }

  if (msg.type === "ticket_created") {
    const { issue_name } = msg.data || {};
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <div className="ticket-created-card">
          <div className="ticket-created-icon">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            </svg>
          </div>
          <div className="ticket-created-info">
            <div className="ticket-created-title">Ticket Created Successfully</div>
            {issue_name && <div className="ticket-created-issue">{issue_name}</div>}
            <div className="ticket-created-hint">
              Check the Raised Tickets section in Help &amp; Support to track it.
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (msg.type === "quick_replies") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <QuickReplies
          data={msg.data || {}}
          onSelect={onQuickReply}
        />
      </div>
    );
  }

  return null;
}
