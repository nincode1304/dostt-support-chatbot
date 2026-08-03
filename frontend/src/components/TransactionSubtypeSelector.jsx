import { useState } from "react";

export default function TransactionSubtypeSelector({ data, onSelect }) {
  const { options = [] } = data;
  const [selected, setSelected] = useState(null);

  function handleClick(opt) {
    if (selected) return;
    setSelected(opt.id);
    onSelect(opt.id);
  }

  return (
    <div className="subtype-selector">
      {options.map((opt) => (
        <button
          key={opt.id}
          className={`subtype-card${selected === opt.id ? " selected" : ""}${selected && selected !== opt.id ? " faded" : ""}`}
          onClick={() => handleClick(opt)}
          disabled={!!selected}
          aria-label={opt.label}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
