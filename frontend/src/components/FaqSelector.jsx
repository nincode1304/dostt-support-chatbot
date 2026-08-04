import { useState } from "react";

export default function FaqSelector({ data, onSelect, disabled: parentDisabled }) {
  const { faqs = [] } = data;
  const [selected, setSelected] = useState(null);

  function handleClick(faq) {
    if (selected || parentDisabled) return;
    setSelected(faq.id);
    onSelect(faq.id, faq.title);
  }

  const isDisabled = parentDisabled || !!selected;

  return (
    <div className="faq-selector">
      {faqs.map((faq) => (
        <button
          key={faq.id}
          className={`faq-card${selected === faq.id ? " selected" : ""}${(isDisabled && selected !== faq.id) ? " faded" : ""}`}
          onClick={() => handleClick(faq)}
          disabled={isDisabled}
          aria-label={faq.title}
        >
          <span className="faq-card-title">{faq.title}</span>
          <span className="faq-card-arrow">›</span>
        </button>
      ))}
    </div>
  );
}
