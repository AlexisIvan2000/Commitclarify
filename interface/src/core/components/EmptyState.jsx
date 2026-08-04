function EmptyState({ icon = null, title, text = null, action = null }) {
  return (
    <div className="empty-state">
      {icon && <span className="empty-state-icon">{icon}</span>}
      <h2 className="empty-state-title">{title}</h2>
      {text && <p className="empty-state-text">{text}</p>}
      {action}
    </div>
  )
}

export default EmptyState
