import { useState } from "react";

export default function QuickReplies({ data, onSelect, disabled: parentDisabled }) {
  const { options = [], disclaimer } = data;
  const [selected, setSelected] = useState(null);

  function handleClick(opt) {
    if (selected || parentDisabled) return;
    setSelected(opt.id);
    onSelect(opt.id, opt.label);
  }

  const isDisabled = parentDisabled || !!selected;

  return (
    <div className="quick-replies-wrapper">
      <div className="quick-replies">
        {options.map((opt) => (
          <button
            key={opt.id}
            className={`quick-reply-btn${isDisabled && selected !== opt.id ? " stale" : ""}`}
            onClick={() => handleClick(opt)}
            disabled={isDisabled}
            aria-label={opt.label}
          >
            {opt.label}
          </button>
        ))}
      </div>
      {disclaimer && (
        <p className="consent-disclaimer">{disclaimer}</p>
      )}
    </div>
  );
}
