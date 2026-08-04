import { useState } from "react";

export default function TransactionSubtypeSelector({ data, onSelect, disabled: parentDisabled }) {
  const { options = [] } = data;
  const [selected, setSelected] = useState(null);

  function handleClick(opt) {
    if (selected || parentDisabled) return;
    setSelected(opt.id);
    onSelect(opt.id, opt.label);
  }

  const isDisabled = parentDisabled || !!selected;

  return (
    <div className="subtype-selector">
      {options.map((opt) => (
        <button
          key={opt.id}
          className={`subtype-card${selected === opt.id ? " selected" : ""}${(isDisabled && selected !== opt.id) ? " faded" : ""}`}
          onClick={() => handleClick(opt)}
          disabled={isDisabled}
          aria-label={opt.label}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
