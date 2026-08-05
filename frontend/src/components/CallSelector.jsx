import { useState } from "react";

export default function CallSelector({ data, onSelect, disabled: parentDisabled }) {
  const { calls = [], prompt } = data;
  const [selected, setSelected] = useState(null);

  function handleSelect(call) {
    if (selected || parentDisabled) return;
    setSelected(call.id);
    const person = call.expert || call.customer || {};
    const name = (person.name || "Unknown").replace(/_/g, " ");
    const label = call.booking_date ? `${name} · ${call.booking_date}` : name;
    onSelect(call.id, label);
  }

  return (
    <div className="entity-selector">
      {calls.map((call) => {
        const person = call.expert || call.customer || {};
        const name = person.name || "Unknown";
        const displayName = name.replace(/_/g, " ");
        const isSelected = selected === call.id;
        const meta = [call.booking_date, call.total_duration, call.type].filter(Boolean).join(" · ");

        return (
          <button
            key={call.id}
            className={`entity-card${isSelected ? " selected" : ""}${(parentDisabled || (!!selected && !isSelected)) ? " faded" : ""}`}
            onClick={() => handleSelect(call)}
            disabled={parentDisabled || !!selected}
            aria-label={`Select call — ${displayName}`}
          >
            <span className="entity-card-icon">
              <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/>
              </svg>
            </span>
            <span className="entity-card-body">
              <span className="entity-card-title">{displayName}</span>
              {meta && <span className="entity-card-meta">{meta}</span>}
            </span>
            {call.coins != null && (
              <span className="entity-card-value">{call.coins} coins</span>
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
