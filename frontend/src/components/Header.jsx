export default function Header() {
  return (
    <div className="header">
      <div className="header-avatar-wrap">
        <div className="header-avatar">
          <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
          </svg>
        </div>
        <span className="header-online-dot" />
      </div>
      <div className="header-info">
        <div className="header-name">Dostt Support</div>
        <div className="header-status">Online</div>
      </div>
      <button className="header-menu-btn" aria-label="More options">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="5" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="12" cy="19" r="1.8"/>
        </svg>
      </button>
    </div>
  );
}
