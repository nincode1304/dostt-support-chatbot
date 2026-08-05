import CallSelector from "./CallSelector";
import CategorySelector from "./CategorySelector";
import FaqSelector from "./FaqSelector";
import QuickReplies from "./QuickReplies";
import TicketConfirmation from "./TicketConfirmation";
import TransactionSelector from "./TransactionSelector";
import TransactionSubtypeSelector from "./TransactionSubtypeSelector";
import { t } from "../translations";

const BotLogo = () => (
  <svg viewBox="0 0 802 671" xmlns="http://www.w3.org/2000/svg">
    <path fillRule="evenodd" clipRule="evenodd" d="M301.646 34.9469C352.366 11.9199 407.504 0 463.297 0C650.358 0 802 150.208 802 335.5C802 520.792 650.358 671 463.297 671C407.504 671 352.366 659.08 301.646 636.053L90.7085 540.287C62.3439 527.41 67.7787 485.973 98.5236 480.702L150.872 471.728C183.235 466.179 186.839 421.566 155.779 410.99L21.431 365.245C-7.14366 355.515 -7.14366 315.485 21.431 305.755L155.779 260.01C186.839 249.434 183.235 204.821 150.872 199.272L98.5236 190.298C67.7788 185.027 62.344 143.59 90.7086 130.712L301.646 34.9469ZM412.794 209.688C412.794 186.526 431.749 167.75 455.132 167.75C478.514 167.75 497.469 186.526 497.469 209.688V293.562C497.469 316.724 478.514 335.5 455.132 335.5C431.749 335.5 412.794 316.724 412.794 293.562V209.688ZM582.145 209.688C582.145 186.526 601.1 167.75 624.483 167.75C647.865 167.75 666.821 186.526 666.821 209.688V293.562C666.821 316.724 647.865 335.5 624.483 335.5C601.1 335.5 582.145 316.724 582.145 293.562V209.688ZM437.491 398.406C423.851 398.406 412.794 409.359 412.794 422.87C412.794 490.424 468.08 545.188 536.279 545.188H543.335C611.534 545.188 666.821 490.424 666.821 422.87C666.821 409.359 655.763 398.406 642.124 398.406H437.491Z" fill="white"/>
  </svg>
);

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

export default function Message({ msg, isActive, language, onSelectCategory, onSelectTransactionSubtype, onSelectFaq, onSelectCall, onSelectTransaction, onConfirmTicket, onEditTicket, onCancelAction, onQuickReply }) {
  const now = Date.now();

  if (msg.type === "text" || msg.type === "chat_ended") {
    return (
      <div className={`message-row ${msg.role}${msg.role === "bot" && msg.type === "error" ? " message-error" : ""}`}>
        {msg.role === "bot" && (
          <div className="bot-avatar">
            <BotLogo />
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
        <CategorySelector data={msg.data || {}} onSelect={onSelectCategory} disabled={!isActive} />
      </div>
    );
  }

  if (msg.type === "transaction_subtype_cards") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <TransactionSubtypeSelector data={msg.data || {}} onSelect={onSelectTransactionSubtype} disabled={!isActive} />
      </div>
    );
  }

  if (msg.type === "faq_cards") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <FaqSelector data={msg.data || {}} onSelect={onSelectFaq} disabled={!isActive} />
      </div>
    );
  }

  if (msg.type === "call_cards") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <CallSelector data={msg.data || {}} onSelect={onSelectCall} disabled={!isActive} />
      </div>
    );
  }

  if (msg.type === "transaction_cards") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <TransactionSelector data={msg.data || {}} onSelect={onSelectTransaction} disabled={!isActive} />
      </div>
    );
  }

  if (msg.type === "ticket_confirmation") {
    return (
      <div className="message-row bot">
        <div className="bot-avatar-spacer" />
        <TicketConfirmation
          data={msg.data || {}}
          disabled={!isActive}
          language={language}
          onConfirm={onConfirmTicket}
          onEdit={onEditTicket}
          onCancel={onCancelAction}
        />
      </div>
    );
  }

  if (msg.type === "ticket_created") {
    const { issue_name, title, hint, ticket_id } = msg.data || {};
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
            <div className="ticket-created-title">{title || t(language, "ticket_created_title")}</div>
            {issue_name && <div className="ticket-created-issue">{issue_name}</div>}
            {ticket_id && <div className="ticket-created-id">#{ticket_id}</div>}
            <div className="ticket-created-hint">
              {hint || t(language, "ticket_created_hint")}
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
          disabled={!isActive}
        />
      </div>
    );
  }

  return null;
}
