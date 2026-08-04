function PageHeader({ icon = null, title, count = null, actions = null }) {
  return (
    <header className="page-header">
      <h1 className="page-title">
        {icon}
        <span>{title}</span>
        {count !== null && <span className="page-count">{count}</span>}
      </h1>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  )
}

export default PageHeader
