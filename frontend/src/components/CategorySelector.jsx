import { useState } from "react";

const ICONS = {
  phone: (
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z" />
    </svg>
  ),
  wallet: (
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M21 18v1c0 1.1-.9 2-2 2H5c-1.11 0-2-.9-2-2V5c0-1.1.89-2 2-2h14c1.1 0 2 .9 2 2v1h-9c-1.11 0-2 .9-2 2v8c0 1.1.89 2 2 2h9zm-9-2h10V8H12v8zm4-2.5c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z" />
    </svg>
  ),
  chat: (
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z" />
    </svg>
  ),
};

export default function CategorySelector({ data, onSelect, disabled: parentDisabled }) {
  const { options = [] } = data;
  const [selected, setSelected] = useState(null);

  function handleClick(opt) {
    if (selected || parentDisabled) return;
    setSelected(opt.id);
    onSelect(opt.id, opt.label);
  }

  const isDisabled = parentDisabled || !!selected;

  return (
    <div className="category-selector">
      {options.map((opt) => (
        <button
          key={opt.id}
          className={`category-card${selected === opt.id ? " selected" : ""}${(isDisabled && selected !== opt.id) ? " faded" : ""}`}
          onClick={() => handleClick(opt)}
          disabled={isDisabled}
          aria-label={opt.label}
        >
          <span className="category-icon">{ICONS[opt.icon] || ICONS.chat}</span>
          <span className="category-label">{opt.label}</span>
          <span className="category-arrow">›</span>
        </button>
      ))}
    </div>
  );
}
