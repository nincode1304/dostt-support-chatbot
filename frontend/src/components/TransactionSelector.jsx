import { useState } from "react";

export default function TransactionSelector({ data, onSelect, disabled: parentDisabled }) {
  const { transactions = [], prompt } = data;
  const [selected, setSelected] = useState(null);

  function handleSelect(tx) {
    if (selected || parentDisabled) return;
    setSelected(tx.id);
    const credit = isCredit(tx);
    const coinsText = tx.coins != null && tx.coins !== 0
      ? ` · ${credit ? "+" : "−"}${tx.coins} coins`
      : "";
    const label = `${typeLabel(tx)}${coinsText}`;
    onSelect(tx.id, label);
  }

  function isCredit(tx) {
    return tx.amount > 0;
  }

  function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleDateString("en-IN", {
        day: "numeric", month: "short", year: "numeric",
      });
    } catch {
      return dateStr;
    }
  }

  function statusLabel(status) {
    if (status === 1) return "success";
    if (status === 2) return "pending";
    if (status === 3) return "failed";
    return String(status ?? "");
  }

  function typeLabel(tx) {
    return tx.title || "Transaction";
  }

  return (
    <div className="entity-selector">
      {transactions.map((tx) => {
        const credit = isCredit(tx);
        const isSelected = selected === tx.id;
        const meta = [formatDate(tx.created_on), tx.status != null ? statusLabel(tx.status) : null].filter(Boolean).join(" · ");

        return (
          <button
            key={tx.id}
            className={`entity-card${isSelected ? " selected" : ""}${(parentDisabled || (!!selected && !isSelected)) ? " faded" : ""}`}
            onClick={() => handleSelect(tx)}
            disabled={parentDisabled || !!selected}
            aria-label={`Select transaction ${typeLabel(tx)}`}
          >
            <span className="entity-card-icon">
              <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M20 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/>
              </svg>
            </span>
            <span className="entity-card-body">
              <span className="entity-card-title">{typeLabel(tx)}</span>
              {meta && <span className="entity-card-meta">{meta}</span>}
            </span>
            {tx.amount != null && (
              <span className="entity-card-value">₹{tx.amount}</span>
            )}
            <svg className="entity-card-arrow" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </button>
        );
      })}
    </div>
  );
}
