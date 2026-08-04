export default function TicketConfirmation({ data, disabled, onConfirm, onEdit, onCancel }) {
  const { description = "", issue_name = "Support Request" } = data;

  return (
    <div className={`ticket-confirmation-card${disabled ? " stale" : ""}`}>
      <div className="ticket-card-header">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V8l8 5 8-5v10zm-8-7L4 6h16l-8 5z"/>
        </svg>
        <span className="ticket-card-title">Create Support Ticket</span>
      </div>

      <div className="ticket-card-label">Issue</div>
      <div className="ticket-card-issue-name">{issue_name}</div>

      <div className="ticket-card-label">Description</div>
      <div className="ticket-card-description">{description}</div>

      <div className="ticket-card-actions">
        <button className="btn btn-confirm" onClick={onConfirm} disabled={disabled} aria-label="Confirm ticket creation">
          Confirm
        </button>
        <button className="btn btn-edit" onClick={onEdit} disabled={disabled} aria-label="Edit ticket description">
          Edit
        </button>
        <button className="btn btn-cancel" onClick={onCancel} disabled={disabled} aria-label="Cancel ticket creation">
          Cancel
        </button>
      </div>
    </div>
  );
}
