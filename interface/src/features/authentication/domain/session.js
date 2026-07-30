import { ApiError, isNetworkFailure, isUnauthorized } from '@core/network/errors'

export const SESSION_STATUS = {
  loading: 'loading',
  authenticated: 'authenticated',
  anonymous: 'anonymous',
  unavailable: 'unavailable',
}

export function shouldEndSession(error) {
  return isUnauthorized(error)
}

export function isTransientFailure(error) {
  return isNetworkFailure(error) || (error instanceof ApiError && error.status >= 500)
}
