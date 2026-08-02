import { useState } from "react";

export default function CallSelector({ data, onSelect }) {
  const { calls = [], prompt } = data;
  const [selected, setSelected] = useState(null);

  function handleSelect(call) {
    if (selected) return; // Already selected — prevent double-tap
    setSelected(call.id);
    onSelect(call.id);
  }

  return (
    <div className="card-wrapper">
      {prompt && <div className="card-prompt">{prompt}</div>}
      <div className="call-cards">
        {calls.map((call) => {
          // USER side uses call.expert, LISTENER side uses call.customer
          const person = call.expert || call.customer || {};
          const name = person.name || "Unknown";
          const displayName = name.replace(/_/g, " ");
          const isSelected = selected === call.id;

          return (
            <button
              key={call.id}
              className={`call-card${isSelected ? " selected" : ""}`}
              onClick={() => handleSelect(call)}
              disabled={!!selected}
              aria-label={`Select call — ${displayName}`}
            >
              <div className="call-card-icon">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/>
                </svg>
              </div>
              <div className="call-card-info">
                <div className="call-card-name">{displayName}</div>
                <div className="call-card-meta">
                  {call.booking_date && <span>{call.booking_date}</span>}
                  {call.total_duration && <span> · {call.total_duration}</span>}
                </div>
                {call.ticket_detail && (
                  <span className="call-card-ticket-badge">Ticket #{call.ticket_detail.id}</span>
                )}
              </div>
              <div className="call-card-right">
                {call.coins != null && (
                  <div className="call-card-coins">{call.coins} coins</div>
                )}
                {call.type && <div className="call-card-type">{call.type}</div>}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
