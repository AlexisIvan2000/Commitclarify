import { Component } from 'react'
import { getStrings } from '../translation'
import ErrorState from './ErrorState'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { failed: false }
    this.reload = () => window.location.reload()
  }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error, info) {
    console.error('Rendu interrompu:', error, info?.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children

    return (
      <div className="callback-error">
        <ErrorState message={getStrings().errors.renderCrash} onRetry={this.reload} />
      </div>
    )
  }
}

export default ErrorBoundary
