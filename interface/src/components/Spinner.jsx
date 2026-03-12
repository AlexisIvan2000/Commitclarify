function Spinner({ text = "Chargement..." }) {
  return (
    <div className="dash-loading">
      <div className="spinner" />
      <p>{text}</p>
    </div>
  )
}

export default Spinner
