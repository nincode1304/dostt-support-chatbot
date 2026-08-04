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
    <div className="card-wrapper">
      {prompt && <div className="card-prompt">{prompt}</div>}
      <div className="transaction-cards">
        {transactions.map((tx) => {
          const credit = isCredit(tx);
          const isSelected = selected === tx.id;

          return (
            <button
              key={tx.id}
              className={`transaction-card${isSelected ? " selected" : ""}${(parentDisabled || (!!selected && !isSelected)) ? " faded" : ""}`}
              onClick={() => handleSelect(tx)}
              disabled={parentDisabled || !!selected}
              aria-label={`Select transaction ${typeLabel(tx)}`}
            >
              <div className={`transaction-card-icon ${credit ? "credit" : "debit"}`}>
                {credit ? (
                  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/>
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M20 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/>
                  </svg>
                )}
              </div>
              <div className="transaction-card-info">
                <div className="transaction-card-desc">{typeLabel(tx)}</div>
                <div className="transaction-card-date">
                  {formatDate(tx.created_on)}
                  {tx.status != null && ` · ${statusLabel(tx.status)}`}
                </div>
              </div>
              <div className="transaction-card-amount">
                {tx.coins != null && tx.coins !== 0 && (
                  <div className={`transaction-card-coins ${credit ? "credit" : "debit"}`}>
                    {credit ? "+" : "−"}{tx.coins} coins
                  </div>
                )}
                {tx.amount != null && (
                  <div className="transaction-card-status">₹{tx.amount}</div>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
