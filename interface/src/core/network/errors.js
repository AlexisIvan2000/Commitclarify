import { getStrings } from '../translation'

export class ApiError extends Error {
  constructor(status, detail, code, params) {
    super(detail || `HTTP ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail || null
    this.code = code || null
    this.params = params || {}
  }
}

export class NetworkError extends Error {
  constructor(cause) {
    super('network')
    this.name = 'NetworkError'
    this.cause = cause
  }
}

export function messageForStatus(status) {
  const { errors } = getStrings()

  if (status === 401) return errors.unauthorized
  if (status === 403) return errors.forbidden
  if (status === 404) return errors.notFound
  if (status === 409) return errors.conflict
  if (status === 429) return errors.quota
  if (status >= 500) return errors.server

  return errors.unexpected
}

export function fillParams(template, params) {
  if (!template || !params) return template

  return Object.entries(params).reduce(
    (text, [key, value]) => text.replaceAll(`{${key}}`, value),
    template,
  )
}

export function messageForCode(code, params) {
  if (!code) return null
  return fillParams(getStrings().apiErrors[code], params) || null
}

export function isUnauthorized(error) {
  return error instanceof ApiError && error.status === 401
}

export function isNetworkFailure(error) {
  return error instanceof NetworkError
}

export function messageOf(error) {
  if (error instanceof NetworkError) return getStrings().errors.network

  if (error instanceof ApiError) {
    return messageForCode(error.code, error.params)
      || error.detail
      || messageForStatus(error.status)
  }

  return getStrings().errors.unexpected
}
