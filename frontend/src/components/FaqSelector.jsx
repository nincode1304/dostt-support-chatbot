import { useState } from "react";

export default function FaqSelector({ data, onSelect }) {
  const { faqs = [] } = data;
  const [selected, setSelected] = useState(null);

  function handleClick(faq) {
    if (selected) return;
    setSelected(faq.id);
    onSelect(faq.id);
  }

  return (
    <div className="faq-selector">
      {faqs.map((faq) => (
        <button
          key={faq.id}
          className={`faq-card${selected === faq.id ? " selected" : ""}${selected && selected !== faq.id ? " faded" : ""}`}
          onClick={() => handleClick(faq)}
          disabled={!!selected}
          aria-label={faq.title}
        >
          <span className="faq-card-title">{faq.title}</span>
          <span className="faq-card-arrow">›</span>
        </button>
      ))}
    </div>
  );
}
