import { useState } from "react";

export default function QuickReplies({ data, onSelect }) {
  const { options = [] } = data;
  const [selected, setSelected] = useState(null);

  function handleClick(opt) {
    if (selected) return;
    setSelected(opt.id);
    onSelect(opt.id);
  }

  return (
    <div className="quick-replies">
      {options.map((opt) => (
        <button
          key={opt.id}
          className="quick-reply-btn"
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
